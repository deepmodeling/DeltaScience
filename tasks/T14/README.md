# 31254.49.DELTASCIENCE.V1.T14 — Joint Optimization of Trap Orientation and Process Control for Robust Selective Release

<p>
  <strong>English</strong> | <a href="./README_zh.md">简体中文</a> · <a href="../README.md">← All Open-Source Tasks</a>
</p>

| Field | Value |
| :--- | :--- |
| **CSTR Persistent Identifier** | [`31254.49.DELTASCIENCE.V1.T14`](https://cstr.cn/31254.49.DELTASCIENCE.V1.T14) |
| **Web Detail Page** | [https://deltascience.bohrium.com/questions/T14](https://deltascience.bohrium.com/questions/T14) |
| **Discipline Group(s)** | Materials Science, Math & CS |
| **Subfield(s)** | Materials Design, Operations Research |
| **Task Type** | Open Design & Search |
| **Evaluation Time Limit** | 1 hour |
| **Contributing Institutions** | DP Technology |

---

## Scientific Objective

Solve a coupled discrete-continuous inverse design problem on a **frustrated amorphous trap network** containing **504 binary trap nodes** ($\pm 1$ orientations across 3 chemical classes of 168 nodes each, with exact class-level inventory balance) and **24 processing zones** (72 continuous variables: annealing temperature, dwell time, and quench rate subject to zone bounds and global budgets). The goal is to maximize the **worst-case selective release yield** (species A release × species B retention) jointly across four intervention families (thermal, flux, isotope, and cyclic) and both forward/reverse histories.

Full problem statement and physics formulation are in [`instruction.md`](./instruction.md), with public network inputs pre-packaged in `registry.dp.tech/public/pkscience-t14-agent`.

## Verification & Reference Notes

- **Deliverable**: `/workspace/outputs/design.json` containing `orientation[504]` and the three length-24 process arrays.
- **Independent Replay**: [`tests/checker.py`](./tests/checker.py) replays the forward physical model independently against private `tests/reference_resources/` (not just the 48 public calibration scenarios) across orientation/process validity, inventory/budget, loop compatibility, nominal yield, and joint worst-case robust yield (64/100 points).
- **Reference Harness**: [`solution/solve.sh`](./solution/solve.sh) invokes `gold_a.py` with `witness.json` for verifier validation (excluded from the Agent container).

## Runtime & Environment

- Linux, 4 CPU, 8 GiB RAM, no GPU; Python 3.12 with `NumPy` and `SciPy` (`environment/Dockerfile`).

## Anti-Contamination & Usage Policy

Per the DeltaScience usage policy, this task package, its instructions, reference artifacts, and grading scripts may **not** be used for model training, fine-tuning, distillation, or synthetic training data generation.
