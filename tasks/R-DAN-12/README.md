# 31254.49.DELTASCIENCE.V1.R.DAN.12 — Open-Route Retrosynthesis & Multi-Route Ranking (Danicopan Series `DAN-US2019-EX395`)

<p>
  <strong>English</strong> | <a href="./README_zh.md">简体中文</a> · <a href="../README.md">← All Open-Source Tasks</a>
</p>

| Field | Value |
| :--- | :--- |
| **CSTR Persistent Identifier** | [`31254.49.DELTASCIENCE.V1.R.DAN.12`](https://cstr.cn/31254.49.DELTASCIENCE.V1.R.DAN.12) |
| **Web Detail Page** | [https://deltascience.bohrium.com/questions/R-DAN-12](https://deltascience.bohrium.com/questions/R-DAN-12) |
| **Discipline Group(s)** | Chemistry |
| **Subfield(s)** | Organic Chemistry, Medicinal Chemistry |
| **Task Type** | Tool-Use & Planning |
| **Evaluation Time Limit** | 8 hours |
| **Contributing Institutions** | DP Technology; University of Tokyo |

---

## Scientific Objective

Plan, validate, and rank complete open-route retrosynthetic pathways for the Danicopan series target **`DAN-US2019-EX395`**. Agents must orchestrate chemistry synthesis tools, verify starting-material availability and step feasibility, and submit ranked synthetic routes meeting strict chemical and formatting contracts.

See [`instruction.md`](./instruction.md) for the full problem statement, tool contract, and submission specification.

## Independent Verification & Dynamic Gold Baseline

- **Dynamic Gold Comparison**: During independent verification under [`tests/`](./tests/), the grader first evaluates the designated gold reference route to obtain baseline score $G$, then evaluates each formally submitted route to obtain $S_i$. The binary acceptance reward is `1` if and only if at least one submitted route achieves $S_i \ge G$; otherwise `0`.
- **Submission Integrity**: Unsubmitted or business-rejected candidates are never backfilled as valid submissions. All raw judge responses, criterion-level scores, and provenance receipts are preserved in verifier logs.
- **Reference Harness**: Reference artifacts are located in [`solution/`](./solution/) (excluded from the Agent execution container).

## Anti-Contamination & Usage Policy

Per the DeltaScience usage policy, this task package, its instructions, reference routes, and grading scripts may **not** be used for model training, fine-tuning, distillation, or synthetic training data generation.
