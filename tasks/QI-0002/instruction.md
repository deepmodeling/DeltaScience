Gate-error tolerance of noise-adapted quantum codes under circuit constraints

Research background

Quantum error correction distributes an unknown logical state across physical qubits. Redundancy can suppress storage errors, but encoding and recovery introduce additional faulty gates. A useful small-device question is therefore not only how well a code performs with ideal controls, but how accurate its gates must be before encoding provides net protection.

Noise also differs between physical qubits. VGQEC used a historical IBM-LIMA coherence-time snapshot to demonstrate that adapted five-qubit codes can outperform a standard five-qubit code. Its thermal-noise simulation assumes ideal encoding and recovery. The authors provide final parameters, so evaluating the result does not require repeating training. Its complete recovery includes fresh auxiliary qubits and standard-code recovery; their implementation costs must both count. VarQEC and Channel-Optimized Quantum Error Correction provide additional methods, but their cost functions do not directly measure net protection with faulty gates.

This task asks whether one finite circuit can retain net protection across noise mismatch while tolerating less accurate gates. Greater tolerance relaxes the control precision required to preserve quantum information. Requiring an advantage in every published condition prevents improvements at one noise point from concealing deterioration elsewhere. The result concerns this model and finite stress set, not a global bound, an entire continuous noise family, or demonstrated hardware performance.

Task

Submit one deterministic encoder/recovery pair that increases gate-error tolerance while outperforming the same-condition bare qubit in every case. Use the same gates and angles for all cases and all gate-error probabilities; no case labels or parameter-dependent switching. Evaluate protection of an arbitrary unknown logical state using Haar-average logical fidelity.

The fixed public reference is `/app/reference.json`: the published VGQEC outcome with complete recovery. `/app/BASELINES.md` specifies provenance, original-condition calibration and compilation. The evaluator recomputes both circuits and never trains or trusts self-reported performance. Only the circuit result is required; a report is unnecessary for numeric scoring.

Physical model and resources

q0 is the logical input/output; q1…q4 start in |0000>. Encoding acts on q0…q4. These five wires undergo one 4 μs memory channel. Only when recovery begins, introduce q5,q6 in |00>; recovery can use all seven wires. Retain q0 and trace out the other six outputs. Input and auxiliary preparation are ideal. Measurement, reset, feedback and postselection are forbidden. In matrix conventions, q0 is the least-significant bit.

Allow all-to-all RX, RY, RZ and directed CX, with at most 256 CX and 256 rotation gates combined across both stages. Rotations mean exp(-iθP/2), with finite radians |θ|≤100π. Every listed gate executes and incurs resource/error cost, including zero-angle rotations; delete an unnecessary gate. There is no additional depth cap.

After each CX apply independently to each operand

\[
\mathcal D_p(\rho)=(1-p)\rho+\frac p3(X\rho X+Y\rho Y+Z\rho Z).
\]

After each rotation apply the same channel to its operand with probability 2p/15. Here p is the total local Pauli-error probability on one CX operand, not the average infidelity of the entire CX. Evaluate 0≤p≤0.01. Additional idle decoherence due to gate duration is outside this model. All complete-recovery gates count; standard recovery is not a free ideal operation.

Storage acts independently on each of the five wires. Excited population decays by exp(-t/T1_i), coherence by exp(-t/T2_i), t=4 μs. The nominal historical paper parameters are:

| Parameter / μs | q0 | q1 | q2 | q3 | q4 |
|---|---:|---:|---:|---:|---:|
| T1 | 97.51 | 127.61 | 92.68 | 79.36 | 19.76 |
| T2 | 178.3 | 109.28 | 120.95 | 35.71 | 19.4 |

Define relaxation rates r1_i=1/T1_i and pure-dephasing rates rφ_i=1/T2_i-r1_i/2. Multiply these two rate vectors by the factors below, then reconstruct T1'_i=1/r1'_i and T2'_i=1/(r1'_i/2+rφ'_i), preserving physical channel validity. The ±25% stresses are explicit benchmark assumptions, not measured drift bounds from the paper.

| Case | Relaxation factors q0…q4 | Pure-dephasing factors q0…q4 |
|---|---|---|
| nominal | 1,1,1,1,1 | 1,1,1,1,1 |
| relaxation_bias | 1.25,1.25,1.25,1.25,1.25 | 0.75,0.75,0.75,0.75,0.75 |
| dephasing_bias | 0.75,0.75,0.75,0.75,0.75 | 1.25,1.25,1.25,1.25,1.25 |
| q0_relaxation | 1.25,1,1,1,1 | 1,1,1,1,1 |
| q0_dephasing | 1,1,1,1,1 | 1.25,1,1,1,1 |
| spatial_shift_A | 1.25,1,1,1,0.75 | 0.75,1,1,1,1.25 |
| spatial_shift_B | 0.75,1,1,1,1.25 | 1.25,1,1,1,0.75 |

`/app/config.json` freezes all parameters and caps. The bare control executes no gates on q0 and outputs it after the identical memory channel; it acquires no artificial control errors as p increases.

Metric and evaluation

Let F_s(p) be average logical fidelity in case s and B_s its bare control. Convert logical Bell entanglement fidelity using F_s=(2Fe+1)/3; this is not worst-input-state fidelity. Net protection requires F_s(p)-B_s>10^-10 in every case.

Tolerance is the upper endpoint of the continuous interval starting at p=0 on which every smaller gate-error probability retains net protection. It is zero when protection already fails at p=0. The evaluator does not assume monotonicity: analytic Lipschitz bounds and adaptive interval refinement produce a conservative lower endpoint and an upper failure witness, with probability bracket width at most 10^-7 and fidelity comparison tolerance 10^-10. If the entire evaluation domain passes, report its endpoint. These are floating-point numerical certificates, not formally verified interval arithmetic; the algorithm is public in `/app/tolerance.py`.

Numeric reward increases only with verified gate-error tolerance. Invalid circuits or lack of net advantage receive no optimization gain. Evaluator, dependency and numerical-certification failures are separate from scientific scores.

Let `t` be the certified tolerance of the submitted circuit, `b` the tolerance independently recomputed for the fixed public reference under the same conditions, and `T = 0.0001` the full-score target. The continuous score is `S = 0.2 × max(0, t) / b` for `t ≤ b`, and `S = 0.2 + 0.8 × min(1, (t − b) / (T − b))` for `t > b`. Thus the reference scores 0.2, `t ≥ T` scores 1, and the unrounded `S ≥ 0.40` corresponds to `t ≥ b + 0.25 × (T − b)`. The full-score target is a scoring anchor, not a proof that an attainable solution exists.

Submission

Write only `/app/outputs/submission.json`, UTF-8 JSON, at most 2,000,000 bytes. NaN, Infinity and symbolic links are forbidden. The following illustrates fields only; it is not an optimized solution:

```json
{
  "schema_version": 2,
  "encoder": [
    {"gate": "RY", "qubits": [0], "theta": 0.25},
    {"gate": "CX", "qubits": [0, 4]}
  ],
  "decoder": [
    {"gate": "CX", "qubits": [5, 0]},
    {"gate": "RZ", "qubits": [0], "theta": -0.25}
  ]
}
```

Lists are ordered by execution. CX uses [control,target] without theta. Rotations have one operand and require theta. Gate objects contain exactly the corresponding example fields. Qubit indices are integers and operands must differ; encoding cannot use q5 or q6. Either list may be empty. schema_version must be integer 2; other root-level fields do not participate in numeric evaluation.

Run `/opt/quantum/legacy/bin/python /app/baseline.py --output /app/outputs/submission.json` to export the public control, or use the public model to study other schemes. `/app/schema.md` defines the interface and `/app/resources.yaml` lists resources. No network or credentials are required. The evaluation operator runs the fixed entry point and reads one numeric score; no extra solver output or manual adjudication is required.

Runtime resources and time limit

The solving environment is Linux with 4 CPUs, 8 GiB RAM, and no GPU. The solving time limit is 12 hours. Independent evaluation after submission does not count toward this time limit.

Runtime commands and strict numeric-array conversion examples: `/app/RUNTIME.md`. Use the explicit interpreter documented there.
