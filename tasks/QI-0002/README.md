# 31254.49.DELTASCIENCE.V1.QI.0002 — Noise-Adapted Quantum Error Correction & Gate-Error Tolerance Optimization

<p>
  <strong>English</strong> | <a href="./README_zh.md">简体中文</a> · <a href="../README.md">← All Open-Source Tasks</a>
</p>

| Field | Value |
| :--- | :--- |
| **CSTR Persistent Identifier** | [`31254.49.DELTASCIENCE.V1.QI.0002`](https://cstr.cn/31254.49.DELTASCIENCE.V1.QI.0002) |
| **Web Detail Page** | [https://deltascience.bohrium.com/questions/QI-0002](https://deltascience.bohrium.com/questions/QI-0002) |
| **Discipline Group(s)** | Physics, Math & CS |
| **Subfield(s)** | Quantum Computing, Coding Theory |
| **Task Type** | Open Design & Search |
| **Evaluation Time Limit** | 12 hours |
| **Contributing Institutions** | DP Technology |

---

## Scientific Objective

Design a single deterministic **encoder + recovery circuit pair** under strict gate-count constraints ($\le 256$ `CX` gates and $\le 256$ single-qubit rotation gates combined, no measurements/reset/feedback/postselection) that maximizes the certified **gate-error tolerance** $t$ while strictly outperforming the bare qubit ($F_s(p) - B_s > 10^{-10}$) across all **7 thermal relaxation/dephasing storage stress conditions** ($4\ \mu\text{s}$ storage).

Full physical model, noise stress table, and JSON schema are specified in [`instruction_en.md`](./instruction_en.md) (Chinese: [`instruction_ch.md`](./instruction_ch.md)).

## Scoring & Verification

- **Deliverable**: `/app/outputs/submission.json` (`schema_version = 2`, ordered `encoder` and `decoder` gate lists).
- **Independent Certification**: The verifier under [`tests/`](./tests/) independently recomputes Haar-average logical fidelity $F_s(p) = (2F_e + 1)/3$ and certifies the continuous net-protection prefix $[0, t]$ using analytic Lipschitz bounds and adaptive interval refinement (bracket width $\le 10^{-7}$).
- **Continuous & Binary Score**: Compared against the published VGQEC reference tolerance $b$ (`0.20` baseline) and full-score anchor $T = 10^{-4}$ (`1.00`), with acceptance threshold $S \ge 0.40$.

## Environment & Provenance

- **Runtime**: Linux, 4 CPU, 8 GiB RAM, no GPU; pinned Python 3.12 (`NumPy 2.2.6`, `SciPy 1.15.3`) at `/opt/quantum/legacy/bin/python`.
- **Reference Literature**: Shao et al., *Variational Graphical Quantum Error Correction Codes (VGQEC)*, `arXiv:2410.02608v2` (see [`BASELINE_REPRODUCTION.md`](./BASELINE_REPRODUCTION.md) and [`SCORING_INTERFACE.md`](./SCORING_INTERFACE.md)).

## Anti-Contamination & Usage Policy

Per the DeltaScience usage policy, this task package, its instructions, and its grading scripts may **not** be used for model training, fine-tuning, distillation, or synthetic training data generation.
