"""Public circuit contract and exact seven-case logical-fidelity evaluation."""
import json
import math
from pathlib import Path

import numpy as np

from quantum import evolve, observable_fidelity, recovery_observable, thermal


def load_config(path=None):
    """Load the frozen scientific model; the grader always uses its trusted copy."""
    target = Path(path) if path is not None else Path(__file__).with_name('config.json')
    return json.loads(target.read_text(encoding='utf-8'))


def validate_pair(pair, cfg):
    """Validate result gates, fresh-wire timing and total published resource caps."""
    if not isinstance(pair, dict):
        raise ValueError('circuit result must be an object')
    cx, rotation = 0, 0
    for stage, wires in [('encoder', 5), ('decoder', 7)]:
        gates = pair.get(stage)
        if not isinstance(gates, list) or len(gates) > 512:
            raise ValueError(stage + ' must be a list with at most 512 gates')
        for g in gates:
            if not isinstance(g, dict) or g.get('gate') not in ('CX', 'RX', 'RY', 'RZ'):
                raise ValueError('allowed gates: CX, RX, RY, RZ')
            name, q = g['gate'], g.get('qubits')
            fields = {'gate', 'qubits'} if name == 'CX' else {'gate', 'qubits', 'theta'}
            if set(g) != fields or not isinstance(q, list) or len(q) != (2 if name == 'CX' else 1):
                raise ValueError('invalid gate fields or arity')
            if any(type(bit) is not int or not 0 <= bit < wires for bit in q) or len(set(q)) != len(q):
                raise ValueError('invalid stage qubits or repeated operand')
            if name == 'CX':
                cx += 1
            else:
                theta = g['theta']
                if type(theta) not in (int, float) or not math.isfinite(theta) or abs(theta) > cfg['max_angle']:
                    raise ValueError('theta must be finite radians with |theta|<=100*pi')
                rotation += 1
    if cx > cfg['max_cx'] or rotation > cfg['max_rotations']:
        raise ValueError('combined encoder+decoder resource cap exceeded')
    return {'cx': cx, 'rotations': rotation}


def bare_fidelities(cfg):
    """Unencoded q0 memory under each identical storage condition; no control gates."""
    t = cfg['storage_time_us']
    return np.array([.5 + (np.exp(-t/c['T1_us'][0]) + 2*np.exp(-t/c['T2_us'][0]))/6 for c in cfg['cases']])


class Evaluator:
    """One validated fixed circuit evaluated at several gate-error probabilities."""
    def __init__(self, pair, cfg):
        self.resources = validate_pair(pair, cfg)
        self.pair, self.cfg, self.cache = pair, cfg, {}
        self.bare = bare_fidelities(cfg)
        self.lipschitz = (2/3) * (2*self.resources['cx'] + cfg['single_error_ratio']*self.resources['rotations'])

    def vector(self, p):
        """Return exact average fidelities; reuse only this immutable circuit's values."""
        if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= self.cfg['p_domain_max']:
            raise ValueError('p outside the public evaluation domain')
        if p in self.cache:
            return self.cache[p].copy()
        v = np.zeros(64, complex)
        v[0] = v[33] = 1/np.sqrt(2)
        rho = evolve(np.outer(v, v.conj()), self.pair['encoder'], self.cfg['single_error_ratio']*p, p)
        observable = recovery_observable(self.pair['decoder'], self.cfg['single_error_ratio']*p, p)
        values = []
        for case in self.cfg['cases']:
            memory = thermal(rho.copy(), self.cfg['storage_time_us'], case['T1_us'], case['T2_us'])
            values.append(observable_fidelity(observable, memory))
        result = np.asarray(values)
        if not np.isfinite(result).all():
            raise ArithmeticError('nonfinite fidelity')
        self.cache[p] = result
        return result.copy()

    def margin(self, p):
        """Minimum same-condition advantage, not difference of two worst fidelities."""
        return float(np.min(self.vector(p) - self.bare))
