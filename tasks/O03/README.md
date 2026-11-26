# 31254.49.DELTASCIENCE.V1.O03 — Cross-Cohort Discovery and Multi-Omics Validation of Pathological Fibroblast States in Prurigo Nodularis

<p>
  <strong>English</strong> | <a href="./README_zh.md">简体中文</a> · <a href="../README.md">← All Open-Source Tasks</a>
</p>

| Field | Value |
| :--- | :--- |
| **CSTR Persistent Identifier** | [`31254.49.DELTASCIENCE.V1.O03`](https://cstr.cn/31254.49.DELTASCIENCE.V1.O03) |
| **Web Detail Page** | [https://deltascience.bohrium.com/questions/O03](https://deltascience.bohrium.com/questions/O03) |
| **Discipline Group(s)** | Life Sciences |
| **Subfield(s)** | Omics, Immunology & Inflammation |
| **Task Type** | Multi-Stage Analysis |
| **Evaluation Time Limit** | 8 hours |
| **Contributing Institutions** | AI for Science Institute, Beijing; Zhejiang University |

---

## Harbor Package & Public Container Images

This directory contains the complete 9-stage Harbor task package (`task.toml`, `environment/Dockerfile`, `steps/` with per-stage instructions and setup scripts, and `steps/v_validation/tests/` with the full `o03_scorer_v2` automated verification suite). Multi-cohort single-cell and proteomics data matrices are pre-packaged inside the public scientific runtime images (`registry.dp.tech/public/pkscience-o03-agent` and `registry.dp.tech/public/pkscience-o03-verifier`).

---

## Scientific Objective

Prurigo Nodularis (PN) is a chronic inflammatory skin disease characterized by severe pruritus and fibrotic skin nodules. While single-cell transcriptomics can reveal disease-associated cellular states and transcriptional programs, differences observed in a single cohort do not necessarily reflect reproducible disease mechanisms—they may be confounded by inter-patient heterogeneity, cell-type composition shifts, tissue compartment sampling, or technical batch effects.

Task `O03` challenges AI agents to execute a **9-stage, end-to-end multi-omics disease mechanism investigation** across independent patient cohorts, disease controls, blinded perturbation experiments, tissue proteomics, and external patient expression cohorts:

1. **Stage A — Independent Discovery**: Quality control, lineage annotation, fibroblast sub-state identification, patient-level compositional and intra-state expression comparisons, pathway & CollecTRI transcription factor analysis, and LIANA cell-cell communication on paired lesional/non-lesional PN skin scRNA-seq (`GSE233280`).
2. **Stage B — Independent Cohort Discovery**: Strict blind replication on an independent paired PN scRNA-seq cohort (`GSE273559`) without accessing Stage A data or outputs.
3. **Stage AB — Cross-Cohort Reproducibility**: Systematic cross-cohort comparison using structured Stage A & B records (`record_id`) to classify shared, cohort-specific, discordant, and underpowered findings.
4. **Stage C — Disease Context & Tissue Compartments**: Multi-compartment analysis (fibroblast, endothelial, mural) comparing PN against atopic dermatitis (AD) and healthy controls (`GSE222840`).
5. **Stage R — Upstream Candidate Response Analysis**: Systematic evaluation of candidate upstream regulators and disease programs across observable reference matrices.
6. **Stage D (Blinded) — Perturbation Response Analysis**: Blinded analysis of human dermal fibroblast log2 expression under encoded treatments and genetic backgrounds (`GSE137108`).
7. **Stage D (Decoded) — Experimental Condition Interpretation**: Integration of decoded treatment/background metadata with frozen Stage D outputs and patient-level evidence from Stages A–C.
8. **Stage E — Patient Tissue Proteomics Validation**: Independent differential proteomics and cross-omics reconciliation (`PXD072618` / `IPX0014987001`), explicitly distinguishing concordant, discordant, and coverage-limited signals.
9. **Stage V — External Patient Validation & Synthesis**: External paired lesional/non-lesional expression validation (`GSE261704`) and final evidence synthesis, strictly separating `observation`, `association`, `experimental_response`, and `causal` claims via `record_id` provenance.

---

## Public Data Sources

- **GSE233280** — Paired lesional/non-lesional PN skin scRNA-seq (PMID: 38246584) · [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE233280)
- **GSE273559** — Independent paired PN skin scRNA-seq cohort (PMID: 37506977) · [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE273559)
- **GSE222840** — PN, atopic dermatitis (AD), and healthy skin scRNA-seq (PMID: 37210042) · [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222840)
- **GSE137108** — Human dermal fibroblast inflammatory / TGF-β stimulation response · [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE137108)
- **PXD072618 / IPX0014987001** — PN, AD, and healthy skin tissue proteomics · [ProteomeXchange](https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD072618)
- **GSE261704** — External paired PN expression validation cohort (PMID: 41333131) · [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE261704)

---

## Anti-Contamination & Usage Policy

Per the DeltaScience usage policy, this task specification and its associated data/rubrics may **not** be used for model training, fine-tuning, distillation, or synthetic training data generation.
