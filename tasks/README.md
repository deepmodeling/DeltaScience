# DeltaScience v1.0 Open-Source Representative Tasks

<p>
  <strong>English</strong> | <a href="./README_zh.md">简体中文</a> · <a href="../README.md">← Back to DeltaScience</a>
</p>

To preserve evaluation integrity and prevent data contamination, the full **65-task DeltaScience v1.0** private benchmark remains non-public during its active evaluation cycle. To support community transparency, reproducibility, and task-authoring onboarding, we open-source **7 representative high-quality tasks** spanning the core scientific domains of DeltaScience v1.0.

Every accepted DeltaScience task is assigned a globally unique, persistent **Common Science and Technology Resource (CSTR)** identifier operated by the Computer Network Information Center (CNIC), Chinese Academy of Sciences under China's national standard *Science and Technology Resource Identifier*.

## Task Directory

| CSTR Identifier | Discipline Group(s) | Scientific Topic | Task Type | Limit | README |
| :--- | :--- | :--- | :--- | :---: | :---: |
| [`31254.49.DELTASCIENCE.V1.C.03`](https://cstr.cn/31254.49.DELTASCIENCE.V1.C.03) | Chemistry, Life Sciences | BCL2 / BCL-XL Selective Molecular Design | Open Design & Search | 5h | [EN](./C-03/README.md) · [ZH](./C-03/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.R.DAN.12`](https://cstr.cn/31254.49.DELTASCIENCE.V1.R.DAN.12) | Chemistry | Danicopan Series (`DAN-US2019-EX395`): Open-Route Retrosynthesis & Multi-Route Ranking | Tool-Use & Planning | 8h | [EN](./R-DAN-12/README.md) · [ZH](./R-DAN-12/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.O03`](https://cstr.cn/31254.49.DELTASCIENCE.V1.O03) | Life Sciences | Cross-Cohort Discovery & Multi-Omics Validation of Pathological Fibroblast States in Prurigo Nodularis | Multi-Stage Analysis | 8h | [EN](./O03/README.md) · [ZH](./O03/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.QI.0002`](https://cstr.cn/31254.49.DELTASCIENCE.V1.QI.0002) | Physics, Math & CS | Noise-Adapted Quantum Error Correction Codes & Gate-Error Tolerance Optimization | Open Design & Search | 12h | [EN](./QI-0002/README.md) · [ZH](./QI-0002/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.FUS.0001`](https://cstr.cn/31254.49.DELTASCIENCE.V1.FUS.0001) | Physics | Tokamak Free-Boundary Equilibrium Optimization (MAST-U Shot 45425) | Simulation & Comp. | 4h | [EN](./FUS-0001/README.md) · [ZH](./FUS-0001/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.T14`](https://cstr.cn/31254.49.DELTASCIENCE.V1.T14) | Materials Science, Math & CS | Joint Optimization of Trap Orientation & Process Control for Robust Selective Release | Open Design & Search | 1h | [EN](./T14/README.md) · [ZH](./T14/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.LH.1`](https://cstr.cn/31254.49.DELTASCIENCE.V1.LH.1) | Physics | Stellarator Quasi-Axisymmetric Boundary Optimization (`PRECISE_QA`) | Open Design & Search | 24h | [EN](./LH-1/README.md) · [ZH](./LH-1/README_zh.md) |

## Standard Harbor Task Structure

Each full Harbor task directory follows a reproducible containerized layout:

```text
<TASK_ID>/
├── README.md             # English task overview, metadata, CSTR, and verification summary
├── README_zh.md          # Chinese task overview
├── instruction.md        # Problem statement, scientific constraints, and deliverable contract
├── task.toml             # Resource limits (CPU/RAM/GPU), timeouts, and metadata
├── environment/          # Dockerfile and pinned scientific dependencies/inputs
├── tests/                # Independent verifier scripts and quantitative acceptance rubrics
└── solution/             # (Where applicable) Reference verification harness
```

## Anti-Contamination & Usage Policy

> **IMPORTANT**: No organization or individual may use DeltaScience tasks—including these open-source representative tasks, instructions, reference solutions, or grading scripts, as well as any paraphrases, translations, or derived variants—for **model training, fine-tuning, distillation, or generating synthetic training data**. Commercial resale or bulk scraping is strictly prohibited.
