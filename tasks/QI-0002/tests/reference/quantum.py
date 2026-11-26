"""Exact density operators; physical q0 is the least-significant bit."""
import numpy as np


def local_unitary(rho, unitary, bit):
    """Apply a one-qubit unitary in place, preserving the reference bit."""
    indices = np.arange(len(rho))
    a = indices[(indices & (1 << bit)) == 0]
    b = a ^ (1 << bit)
    x, y = rho[a].copy(), rho[b].copy()
    rho[a] = unitary[0, 0] * x + unitary[0, 1] * y
    rho[b] = unitary[1, 0] * x + unitary[1, 1] * y
    x, y = rho[:, a].copy(), rho[:, b].copy()
    rho[:, a] = unitary[0, 0].conjugate() * x + unitary[0, 1].conjugate() * y
    rho[:, b] = unitary[1, 0].conjugate() * x + unitary[1, 1].conjugate() * y
    return rho


def pauli_noise(rho, p, bit):
    """Apply (1-p)rho+p/3*(XrhoX+YrhoY+ZrhoZ) in place."""
    if p == 0:
        return rho
    indices = np.arange(len(rho))
    a = indices[(indices & (1 << bit)) == 0]
    b = a ^ (1 << bit)
    aa, bb = rho[np.ix_(a, a)].copy(), rho[np.ix_(b, b)].copy()
    rho[np.ix_(a, a)] = (1 - 2 * p / 3) * aa + 2 * p / 3 * bb
    rho[np.ix_(b, b)] = (1 - 2 * p / 3) * bb + 2 * p / 3 * aa
    rho[np.ix_(a, b)] *= 1 - 4 * p / 3
    rho[np.ix_(b, a)] *= 1 - 4 * p / 3
    return rho


def evolve(rho, gates, p_single, p_pair):
    """Execute every submitted gate, then local Pauli noise on each operand."""
    indices = np.arange(len(rho))
    for g in gates:
        name, q = g['gate'], g['qubits']
        if name == 'CX':
            permutation = indices ^ (((indices >> q[0]) & 1) << q[1])
            rho = rho[np.ix_(permutation, permutation)]
        elif name == 'RZ':
            phases = np.exp(-.5j * g['theta'] * (1 - 2 * ((indices >> q[0]) & 1)))
            rho *= phases[:, None]
            rho *= phases.conj()[None, :]
        else:
            c, s = np.cos(g['theta'] / 2), np.sin(g['theta'] / 2)
            m = np.array([[c, -1j*s], [-1j*s, c]]) if name == 'RX' else np.array([[c, -s], [s, c]], complex)
            rho = local_unitary(rho, m, q[0])
        for bit in q:
            rho = pauli_noise(rho, p_pair if name == 'CX' else p_single, bit)
    return rho


def thermal(rho, time_us, t1, t2):
    """Independent zero-temperature thermal channels with coherence exp(-t/T2)."""
    indices = np.arange(len(rho))
    for bit, (a1, a2) in enumerate(zip(t1, t2)):
        a = indices[(indices & (1 << bit)) == 0]
        b = a ^ (1 << bit)
        old = rho.copy()
        survival, coherence = np.exp(-time_us / a1), np.exp(-time_us / a2)
        rho[np.ix_(a, a)] = old[np.ix_(a, a)] + (1-survival) * old[np.ix_(b, b)]
        rho[np.ix_(b, b)] = survival * old[np.ix_(b, b)]
        rho[np.ix_(a, b)] = coherence * old[np.ix_(a, b)]
        rho[np.ix_(b, a)] = coherence * old[np.ix_(b, a)]
    return rho


def fresh_recovery_wires(rho):
    """Insert two clean recovery wires between five stored bits and the reference."""
    out = np.zeros((256, 256), complex)
    indices = np.concatenate([np.arange(32), np.arange(32) + 128])
    out[np.ix_(indices, indices)] = rho
    return out


def average_fidelity(rho):
    """Trace six physical outputs and convert logical Bell fidelity to Haar average."""
    a, b = np.arange(0, 128, 2), np.arange(129, 256, 2)
    fe = float(np.real(np.sum(rho[a, a] + rho[b, b] + rho[a, b] + rho[b, a])) / 2)
    if abs(np.trace(rho)-1) > 1e-9 or not -1e-10 <= fe <= 1+1e-10:
        raise ArithmeticError('nonphysical logical channel')
    return (2 * fe + 1) / 3


def recovery_observable(gates, p_single, p_pair):
    """Pull the Bell test through recovery once, then restrict the fresh wires.

    Local Pauli channels are self-adjoint. Their adjoint precedes the inverse
    unitary when reversing a noisy gate. This observable works for every
    stored state, allowing all stress cases to share one recovery calculation.
    """
    out = np.zeros((256, 256), complex)
    a, b = np.arange(0, 128, 2), np.arange(129, 256, 2)
    out[a, a] = out[b, b] = out[a, b] = out[b, a] = .5
    for g in reversed(gates):
        for bit in g['qubits']:
            out = pauli_noise(out, p_pair if g['gate'] == 'CX' else p_single, bit)
        inverse = dict(g, **({'theta': -g['theta']} if 'theta' in g else {}))
        out = evolve(out, [inverse], 0., 0.)
    indices = np.concatenate([np.arange(32), np.arange(32)+128])
    return out[np.ix_(indices, indices)]


def observable_fidelity(observable, rho):
    """Evaluate a pulled-back Bell test on a normalized stored density operator."""
    fe = np.sum(observable * rho.T)
    if abs(fe.imag) > 1e-9 or abs(np.trace(rho)-1) > 1e-9 or not -1e-10 <= fe.real <= 1+1e-10:
        raise ArithmeticError('nonphysical observable evaluation')
    return (2 * float(fe.real) + 1) / 3
