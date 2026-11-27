# 31254.49.DELTASCIENCE.V1.FUS.0001 — Tokamak Free-Boundary Equilibrium Optimization (MAST-U Discharge 45425)

<p>
  <strong>English</strong> | <a href="./README_zh.md">简体中文</a> · <a href="../README.md">← All Open-Source Tasks</a>
</p>

| Field | Value |
| :--- | :--- |
| **CSTR Persistent Identifier** | [`31254.49.DELTASCIENCE.V1.FUS.0001`](https://cstr.cn/31254.49.DELTASCIENCE.V1.FUS.0001) |
| **Web Detail Page** | [https://deltascience.bohrium.com/questions/FUS-0001](https://deltascience.bohrium.com/questions/FUS-0001) |
| **Discipline Group(s)** | Physics |
| **Subfield(s)** | Fusion & Plasma |
| **Task Type** | Simulation & Comp. |
| **Evaluation Time Limit** | 4 hours |
| **Contributing Institutions** | DP Technology |

---

## Scientific Objective

Improve a static axisymmetric **free-boundary Grad–Shafranov equilibrium solver** under fixed physical inputs for all **212 time slices** of MAST-U conventional-divertor discharge **45425**, minimizing core plasma-boundary discrepancies against the EFIT++ reference branch while strictly preserving machine geometry, active/passive conductor currents, plasma current $I_p$, and Lao profile parameters.

Full physical constraints and input schemas are specified in [`instruction.md`](./instruction.md).

## Deliverables & Acceptance Criteria

- **Deliverables**: `/root/outputs/submission/` containing `flux.npz` (`case_id` for all 212 slices and `psi_Wb` of shape `(212, 65, 65)` in total poloidal flux Wb on $R \in [0.06, 2.0]\text{ m}, Z \in [-2.2, 2.2]\text{ m}$), `solve.py` or `solve.sh`, and `method.md`.
- **Metric**: Using the frozen separatrix diagnostic (`tests/metric_core.py`), the verifier computes the per-slice maximum directional core-boundary deviation $\zeta$ across 360 poloidal angles and evaluates the linear 95th percentile $E = 0.55 z_{200} + 0.45 z_{201}$.
- **Scoring**: Official FreeGSNKE baseline $E_0 = 35.109\text{ mm}$ scores `0.20`; $E \le 30\text{ mm}$ scores `1.00`; $E \ge 50\text{ mm}$ scores `0.00`; acceptance requires continuous score $Q \ge 0.40$ ($E \le 33.83\text{ mm}$).

## Environment & Provenance

- **Runtime**: Linux, 2 CPU, 4096 MiB RAM; pinned Python 3.12 stack at `/opt/challenge-runtime/mastu` (`NumPy`, `SciPy`, `freegs4e`, `Shapely`, `Numba`, `h5py`).
- **Source Paper & Data**: Pentland et al., *Physica Scripta* 100 (2025) 025608 (`DOI: 10.1088/1402-4896/ada192`); archived dataset `DOI: 10.14468/26m5-ey02`.

## Anti-Contamination & Usage Policy

Per the DeltaScience usage policy, this task package, its instructions, and its grading scripts may **not** be used for model training, fine-tuning, distillation, or synthetic training data generation.
