"""Published-outcome calibration, independent channels and continuous certificates."""
import csv
import json
from pathlib import Path
import sys
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'reference'))
from model import Evaluator, bare_fidelities, load_config, validate_pair
from quantum import average_fidelity, evolve, fresh_recovery_wires, local_unitary, observable_fidelity, pauli_noise, recovery_observable, thermal
from tolerance import certify


class PhysicsTests(unittest.TestCase):
    """Compare actual task computation to independently specified physical outcomes."""
    def test_published_five_outcomes(self):
        cfg = load_config()
        cfg['cases'] = cfg['cases'][:1]
        with (HERE / 'fixtures/paper-figure.csv').open() as stream:
            expected = {int(r['time_us']): float(r['channel_fidelity']) for r in csv.DictReader(stream) if r['curve'] == 'VGQEC'}
        for t in [2, 4, 6, 8, 10]:
            with self.subTest(t=t):
                cfg['storage_time_us'] = t
                pair = json.loads((HERE / f'fixtures/published-t{t}.json').read_text())
                measured = Evaluator(pair, cfg).vector(0)[0]
                self.assertAlmostEqual((3*measured-1)/2, expected[t], delta=1e-7)

    def test_bare_exact_and_cache_isolation(self):
        cfg = load_config()
        e = Evaluator({'encoder': [], 'decoder': []}, cfg)
        np.testing.assert_allclose(e.vector(0), bare_fidelities(cfg), atol=1e-14)
        np.testing.assert_allclose(e.vector(.01), bare_fidelities(cfg), atol=1e-14)
        vector = e.vector(0)
        vector[:] = 0
        self.assertTrue(np.all(e.vector(0) > .9))
        self.assertAlmostEqual(e.margin(0), 0, delta=1e-14)
        for p in [-1, float('nan'), True, .02]:
            with self.assertRaises(ValueError): e.vector(p)

    def test_channel_components_against_kraus(self):
        rng = np.random.default_rng(17)
        v = rng.normal(size=4) + 1j*rng.normal(size=4)
        rho = np.outer(v, v.conj()) / np.vdot(v, v)
        paulis = [np.array([[0, 1], [1, 0]]), np.array([[0, -1j], [1j, 0]]), np.diag([1, -1])]
        for bit in [0, 1]:
            lift = lambda x: np.kron(np.eye(2), x) if bit == 0 else np.kron(x, np.eye(2))
            p = .02
            expected = (1-p)*rho + sum(p/3 * lift(x) @ rho @ lift(x).conj().T for x in paulis)
            np.testing.assert_allclose(pauli_noise(rho.copy(), p, bit), expected, atol=1e-15)
        theta = .41
        u = np.array([[np.cos(theta/2), -1j*np.sin(theta/2)], [-1j*np.sin(theta/2), np.cos(theta/2)]])
        lifted = np.kron(np.eye(2), u)
        np.testing.assert_allclose(local_unitary(rho.copy(), u, 0), lifted @ rho @ lifted.conj().T, atol=1e-15)
        a, b = np.diag([1, np.sqrt(.8)]), np.array([[0, np.sqrt(.2)], [0, 0]])
        ad = sum(np.kron(np.eye(2), k) @ rho @ np.kron(np.eye(2), k).conj().T for k in [a, b])
        # T2=2*T1 is the pure amplitude-damping boundary.
        t1 = -1/np.log(.8)
        np.testing.assert_allclose(thermal(rho.copy(), 1, [t1], [2*t1]), ad, atol=1e-15)

    def test_gates_and_physical_guard(self):
        rho = np.zeros((4, 4), complex); rho[0, 0] = 1
        gates = [{'gate': 'RX', 'qubits': [0], 'theta': np.pi}, {'gate': 'CX', 'qubits': [0, 1]},
                 {'gate': 'RY', 'qubits': [1], 'theta': np.pi/2}, {'gate': 'RZ', 'qubits': [0], 'theta': .7}]
        out = evolve(rho.copy(), gates, .0002, .0015)
        self.assertAlmostEqual(np.trace(out).real, 1)
        self.assertGreaterEqual(float(np.linalg.eigvalsh(out).min()), -1e-14)
        with self.assertRaises(ArithmeticError): average_fidelity(np.zeros((256, 256), complex))

    def test_cptp_stresses_and_no_dominating_fixed_bare_wire(self):
        cfg = load_config()
        bell = np.array([1, 0, 0, 1]) / np.sqrt(2)
        all_bare = []
        for case in cfg['cases']:
            for t1, t2 in zip(case['T1_us'], case['T2_us']):
                out = thermal(np.outer(bell, bell), 4, [t1], [t2])
                self.assertGreaterEqual(float(np.linalg.eigvalsh(out).min()), -1e-14)
                self.assertAlmostEqual(float(np.trace(out)), 1.)
            bare = [.5+(np.exp(-4/t1)+2*np.exp(-4/t2))/6 for t1,t2 in zip(case['T1_us'],case['T2_us'])]
            all_bare.append(bare)
        # q0 need not be best in every stress; no fixed alternative dominates
        # the logical input/output port over the whole uncertainty set.
        self.assertAlmostEqual(all_bare[0][0], max(all_bare[0]))
        for bit in range(1,5):
            self.assertTrue(any(row[0] > row[bit] for row in all_bare))

    def test_adjoint_matches_forward_noisy_recovery(self):
        cfg = load_config(); case = cfg['cases'][0]
        v = np.zeros(64, complex); v[0] = v[33] = 1/np.sqrt(2)
        encoder = [{'gate':'RX','qubits':[0],'theta':.4}, {'gate':'CX','qubits':[0,4]}]
        decoder = [{'gate':'RZ','qubits':[4],'theta':.7}, {'gate':'CX','qubits':[4,6]},
                   {'gate':'RX','qubits':[6],'theta':.2}, {'gate':'CX','qubits':[6,0]},
                   {'gate':'RY','qubits':[5],'theta':.3}, {'gate':'CX','qubits':[5,0]}]
        rho = evolve(np.outer(v,v.conj()),encoder,.0004,.003)
        memory = thermal(rho,4,case['T1_us'],case['T2_us'])
        forward = average_fidelity(evolve(fresh_recovery_wires(memory),decoder,.0004,.003))
        backward = observable_fidelity(recovery_observable(decoder,.0004,.003),memory)
        self.assertAlmostEqual(forward,backward,delta=1e-14)
        with self.assertRaises(ArithmeticError): observable_fidelity(np.eye(64)*2,memory)


class ContractTests(unittest.TestCase):
    """Check rejection boundaries that would alter physical resources or inputs."""
    def test_reference_and_caps(self):
        cfg = load_config()
        pair = json.loads((HERE / 'reference/reference.json').read_text())
        self.assertEqual(validate_pair(pair, cfg), {'cx': 234, 'rotations': 247})
        self.assertEqual(validate_pair({'encoder': [], 'decoder': []}, cfg)['cx'], 0)
        for gate in [{'gate': 'CX', 'qubits': [0, 1]}, {'gate': 'RX', 'qubits': [0], 'theta': 0.}]:
            with self.assertRaises(ValueError): validate_pair({'encoder': [gate]*257, 'decoder': []}, cfg)

    def test_invalid_gates(self):
        cfg = load_config()
        bad = [None, {}, {'encoder': (), 'decoder': []}, {'encoder': [0]*513, 'decoder': []}]
        gates = [None, {'gate': 'H', 'qubits': [0]}, {'gate': 'CX', 'qubits': [0]},
                 {'gate': 'CX', 'qubits': [0, 0]}, {'gate': 'CX', 'qubits': [0, True]},
                 {'gate': 'CX', 'qubits': [0, 7]}, {'gate': 'CX', 'qubits': [0, 1], 'theta': 1},
                 {'gate': 'RX', 'qubits': [0]}, {'gate': 'RY', 'qubits': [5], 'theta': 1},
                 {'gate': 'RX', 'qubits': [0], 'theta': True}, {'gate': 'RZ', 'qubits': [0], 'theta': float('nan')},
                 {'gate': 'RZ', 'qubits': [0], 'theta': 400}]
        bad += [{'encoder': [g], 'decoder': []} for g in gates]
        for pair in bad:
            with self.subTest(pair=pair), self.assertRaises(ValueError): validate_pair(pair, cfg)


class CertificateTests(unittest.TestCase):
    """Challenge hidden failures and unresolved interiors, not merely bisection."""
    def setUp(self):
        self.cfg = load_config()

    def test_nonmonotonic_hidden_dip(self):
        # Endpoints both pass; the interior fails then recovers.
        result = certify(lambda p: (p-.002)*(p-.003), .015, self.cfg)
        self.assertLess(result['tolerance'], .002)
        self.assertGreater(result['upper'], .001999)
        self.assertLessEqual(result['upper']-result['tolerance'], 1e-7)
        self.assertTrue(any(s['minimum_advantage'] <= 1e-10 for s in result['samples']))

    def test_safe_and_no_advantage(self):
        self.assertEqual(certify(lambda p: .1, 0, self.cfg)['status'], 'SAFE_THROUGH_DOMAIN')
        self.assertEqual(certify(lambda p: 0, 1, self.cfg)['tolerance'], 0)

    def test_failures_are_not_zero_performance(self):
        with self.assertRaises(ArithmeticError): certify(lambda p: float('nan'), 1, self.cfg)
        cfg = dict(self.cfg, max_evaluations=1)
        with self.assertRaises(ArithmeticError): certify(lambda p: .1, 1, cfg)
        cfg = dict(self.cfg, minimum_interval_width=.1)
        with self.assertRaises(ArithmeticError): certify(lambda p: .0001, 100, cfg)


if __name__ == '__main__':
    unittest.main()
