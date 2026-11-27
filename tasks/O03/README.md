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
| **Resources** | 4 CPUs · 16 GB RAM |
| **Contributing Institutions** | AI for Science Institute, Beijing; Zhejiang University |

---

## Harbor Package & Data Layout

This directory contains the standardized Harbor `v1.1.0` task package (`instruction.md`, `task.toml`, `environment/Dockerfile` based on public `python:3.13.5-slim`, public pathway/regulon/ligand-receptor resources under `environment/resources/`, the complete independent verification suite under `tests/` including `o03_scorer_v2` and `o03_atomwise`, and the reference harness under `solution/`).

Because the raw single-cell matrices under `environment/inputs/` total **~1.46 GB** (with individual `.mtx.gz` files exceeding GitHub's 100 MB limit), `environment/inputs/` is documented via [`environment/inputs/README.md`](./environment/inputs/README.md) with the complete file manifest and original public GEO/ProteomeXchange accessions.

---

## Scientific Objective

Prurigo Nodularis (PN) is a chronic inflammatory skin disease characterized by severe pruritus and fibrotic skin nodules. While single-cell transcriptomics can reveal disease-associated cellular states and transcriptional programs, differences observed in a single cohort do not necessarily reflect reproducible disease mechanisms—they may be confounded by inter-patient heterogeneity, cell-type composition shifts, tissue compartment sampling, or technical batch effects.

Task `O03` challenges AI agents to execute an **integrative, 9-stage patient-level multi-omics investigation** under `/workspace/output` (see [`instruction.md`](./instruction.md)):

1. **Stage `A` (`stages/a_discovery`)**: Independent discovery on paired lesional/non-lesional PN skin scRNA-seq (`GSE233280`)—QC, graph construction, lineage & fibroblast sub-state annotation, patient-level composition/expression, pathway, CollecTRI regulon, and LIANA cell communication.
2. **Stage `B` (`stages/b_replication`)**: Independent replication on a separate paired PN scRNA-seq cohort (`GSE273559`).
3. **Stage `AB` (`stages/b_compare`)**: Cross-cohort reproducibility analysis classifying replicated, cohort-specific, conflicting, and coverage-limited findings.
4. **Stage `C` (`stages/c_context`)**: Disease-context and tissue-compartment analysis (fibroblast, endothelial, mural) across PN, atopic dermatitis (AD), and healthy skin (`GSE222840`).
5. **Stage `R` (`stages/r_response`)**: Upstream candidate response ranking against the fixed response resource (`environment/resources/stage_response_reference.tsv`).
6. **Stage `D_BLIND` (`stages/d_blind`)**: Blinded analysis of encoded human dermal fibroblast perturbation experiments (`GSE137108`).
7. **Stage `D_DECODE` (`stages/d_decode`)**: Decoded experimental interpretation integrating `D_key/condition_key.csv` with patient-level evidence.
8. **Stage `E` (`stages/e_proteome`)**: Patient-tissue proteomics validation (`PXD072618` / `IPX0014987001`), accounting for missingness and acquisition structure.
9. **Stage `V` (`stages/v_validation`)**: External paired-patient expression validation (`GSE261704`) and integrated evidence synthesis strictly distinguishing `observation`, `association`, `experimental_response`, and `causal` inference.

---

## Independent Verification

The separate verifier (`tests/Dockerfile` on `python:3.13.5-slim`) assembles all 9 stage directories without executing submitted code, validates schema compliance and `record_id` provenance, and evaluates **43 scoring atoms** across process evidence, biological results, and structured interpretations. The 100-point continuous scientific score is preserved in `score.json` and `run_report.json`, with binary acceptance at **$\ge 70 / 100$**.

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

Per the DeltaScience usage policy, this task package, its instructions, reference artifacts, and grading scripts may **not** be used for model training, fine-tuning, distillation, or synthetic training data generation.
