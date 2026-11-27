# 31254.49.DELTASCIENCE.V1.C.03 — BCL2 / BCL-XL Selective Molecular Design

<p>
  <strong>English</strong> | <a href="./README_zh.md">简体中文</a> · <a href="../README.md">← All Open-Source Tasks</a>
</p>

| Field | Value |
| :--- | :--- |
| **CSTR Persistent Identifier** | [`31254.49.DELTASCIENCE.V1.C.03`](https://cstr.cn/31254.49.DELTASCIENCE.V1.C.03) |
| **Web Detail Page** | [https://deltascience.bohrium.com/questions/C-03](https://deltascience.bohrium.com/questions/C-03) |
| **Discipline Group(s)** | Chemistry, Life Sciences |
| **Subfield(s)** | Medicinal Chemistry, Cheminformatics, Structural Biology |
| **Task Type** | Open Design & Search |
| **Evaluation Time Limit** | 5 hours |
| **Contributing Institutions** | DP Technology; AI for Science Institute, Beijing |

---

## Scientific Objective

Design a chemically diverse portfolio of small-molecule ligands that achieve strong, selective binding to **BCL2** (`6O0K`, chain A) while suppressing off-target binding to **BCL-XL** (`4QVX`, chain A), satisfying strict medicinal-chemistry, physicochemical, structural, and diversity constraints.

Full problem rules, computational score definitions, and required output files are specified in [`instruction.md`](./instruction.md) and pre-packaged inside the public scientific runtime image (`registry.dp.tech/public/pkscience-c-03-agent`).

## Verification & Reference Status

- **Independent Verification**: The verifier under [`tests/`](./tests/) reads only the declared molecular data artifacts and independently recomputes all docking, selectivity, and portfolio metrics. Public completion reports are solver-side feedback only and are never trusted as final reward.
- **Reference Solution Status**: No executable `solution/` oracle portfolio is bundled in this release; solvers must optimize candidate portfolios from the public structural inputs and completion checker.

## Runtime & Environment

- **Scientific Runtime**: Immutable Linux/amd64 container providing Python 3.11, AutoDock Vina 1.2.7, tmux 3.5a, and hash-locked Python dependencies (`environment/Dockerfile` and `environment/runtime-base.Dockerfile`).
- **Build**: `docker buildx build --platform linux/amd64 -f environment/runtime-base.Dockerfile .` reproduces the base dependency stack from pinned lock files.

## Anti-Contamination & Usage Policy

Per the DeltaScience usage policy, this task package, its instructions, and its grading scripts may **not** be used for model training, fine-tuning, distillation, or synthetic training data generation.
