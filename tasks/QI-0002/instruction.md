Design a single deterministic pair of quantum encoding and recovery circuits that maximizes certified gate-error tolerance while strictly outperforming the bare qubit across all seven thermal-noise storage conditions.

Physical model and constraints (`/app/config.json` freezes all parameters):
- q0 holds the unknown logical input/output state; q1..q4 start in |0000>. The encoder acts on q0..q4, followed by a 4 us independent thermal relaxation/dephasing storage channel on those five qubits.
- At recovery, fresh auxiliary qubits q5 and q6 start in |00>; the decoder acts on q0..q6. Retain q0 and trace out q1..q6. Measurement, reset, classical feedback, and postselection are forbidden. q0 is the least-significant bit in matrix conventions.
- Allowed gates: all-to-all RX, RY, RZ (finite angles |theta| <= 100*pi), and directed CX. Total gate budget across encoder and decoder combined: at most 256 CX gates and at most 256 rotation gates. Every listed gate (including zero-angle rotations) incurs noise.
- Gate noise: after each CX, apply an independent local depolarizing Pauli channel of total error probability p to each operand; after each rotation, apply the same channel with probability 2p/15 to its operand, for p in [0, 0.01].
- Storage stress set: seven conditions (nominal, relaxation_bias, dephasing_bias, q0_relaxation, q0_dephasing, spatial_shift_A, spatial_shift_B) specified in `/app/config.json`. The exact same circuit and angles must be used for all seven conditions and all p.

Evaluation metric:
- Haar-average logical fidelity F_s(p) = (2*F_e + 1) / 3 must strictly exceed the bare-qubit fidelity B_s by more than 1e-10 in every condition s.
- Gate-error tolerance t is the upper endpoint of the continuous interval starting at p = 0 where net protection holds across all seven conditions, certified via analytic Lipschitz bounds and adaptive refinement (public implementation in `/app/tolerance.py`, bracket width <= 1e-7).
- Continuous score scales from 0.2 at the public reference circuit (`/app/reference.json`) to 1.0 at t >= 1e-4.

Deliverable:
Write `/app/outputs/submission.json` (UTF-8 JSON, <= 2 MB, no NaN/Infinity or symlinks) with integer `schema_version: 2`, `encoder` (gate list using q0..q4 only), and `decoder` (gate list using q0..q6). Each rotation gate has `gate`, `qubits`, `theta`; each CX gate has `gate`, `qubits: [control, target]`.

Use `/opt/quantum/legacy/bin/python` (matches the verifier runtime). Time limit: 12 hours (4 CPUs, 8 GiB RAM). Do not use online solutions specific to this task.
