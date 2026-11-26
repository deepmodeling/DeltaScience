# 31254.49.DELTASCIENCE.V1.LH.1 — Stellarator Quasi-Axisymmetric Boundary Optimization (`PRECISE_QA`)

<p>
  <strong>English</strong> | <a href="./README_zh.md">简体中文</a> · <a href="../README.md">← All Open-Source Tasks</a>
</p>

| Field | Value |
| :--- | :--- |
| **CSTR Persistent Identifier** | [`31254.49.DELTASCIENCE.V1.LH.1`](https://cstr.cn/31254.49.DELTASCIENCE.V1.LH.1) |
| **Web Detail Page** | [https://deltascience.bohrium.com/questions/LH-1](https://deltascience.bohrium.com/questions/LH-1) |
| **Discipline Group(s)** | Physics |
| **Subfield(s)** | Fusion & Plasma |
| **Task Type** | Open Design & Search |
| **Evaluation Time Limit** | 24 hours |
| **Contributing Institutions** | DP Technology |

---

## Scientific Objective

Starting from a simple circular-cross-section torus with field-period number $n_{\text{fp}} = 2$, optimize the 3D plasma boundary Fourier representation (`/app/boundary.json`) to achieve a compact **quasi-axisymmetric (QA) stellarator** configuration with aspect ratio $A \le 6$ while simultaneously satisfying strict physics thresholds on quasi-symmetry error, magnetic well, rotational transform, effective ripple, and energetic-particle confinement.

Full physics definitions, normalization conventions (effective minor radius $1.70\text{ m}$, on-axis Boozer field $B_{00} = 5.70\text{ T}$), and acceptance thresholds are specified in [`instruction.md`](./instruction.md).

## Self-Contained Containerized Build & Local Usage

Both `environment/Dockerfile` (Agent image) and `tests/Dockerfile` (independent Verifier image) share an identical pinned scientific stack built from `python:3.12-slim-bookworm` plus bundled source archives in `build-inputs/` (`STELLOPT` / `VMEC2000` / `NEO`, `SIMPLE`, `libneo`, `simsopt`, `jax`/`jaxlib`, `booz_xform`, `OpenMPI`, `gfortran`, `HDF5`, `netCDF-Fortran`). See [`UPSTREAM.md`](./UPSTREAM.md) and `environment/build-inputs/SOURCES.md` for SHA-256 checksums and upstream citations (Landreman & Paul, *Phys. Rev. Lett.* 128, 035001, 2022).

```bash
bash build.sh                               # Build agent & verifier images (verifier reuses runtime cache)
bash run.sh                                 # Interactive solving session mounted at /work
bash evaluate.sh work/boundary.json         # Evaluate a candidate boundary with the verifier image
bash run-reference.sh                       # Recompute reference solution
```

- **Resources**: Linux/amd64 (AVX required for `jaxlib`), 24 CPU, 64 GiB RAM, 20 GiB disk; 24h agent time limit, 12h verifier time limit; no external network during execution.
- **Verification**: Independent verifier writes `reward.txt` (`1` iff aspect ratio $A \le 6$ and all physics thresholds pass; `0` otherwise) and `result.json`.

## Anti-Contamination & Usage Policy

Per the DeltaScience usage policy, this task package, its instructions, reference solutions, and grading scripts may **not** be used for model training, fine-tuning, distillation, or synthetic training data generation.
