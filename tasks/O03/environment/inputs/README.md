# O03 Raw Input Datasets (`environment/inputs/`)

The complete raw input directory contains **95 files (~1.46 GB)** across cohorts `A`, `B`, `C`, `D`, `D_key`, `E`, and `V` (including single-cell count matrices exceeding GitHub's 100 MB per-file limit, such as `C/C_S03_matrix.mtx.gz` and `C/C_S11_matrix.mtx.gz`).

These matrices are derived from public biomedical repositories:
- **Cohort A** (`GSE233280`): [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE233280)
- **Cohort B** (`GSE273559`): [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE273559)
- **Cohort C** (`GSE222840`): [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222840)
- **Cohort D / D_key** (`GSE137108`): [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE137108)
- **Cohort E** (`PXD072618` / `IPX0014987001`): [ProteomeXchange](https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD072618)
- **Cohort V** (`GSE261704`): [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE261704)

For the exact folder-to-stage mapping and metadata contract, see `../task_meta.json`.

## File Manifest

| Relative Path | Size |
| :--- | ---: |
| `A/A_S01_barcodes.tsv.gz` | 14.2 KB |
| `A/A_S01_features.tsv.gz` | 333.4 KB |
| `A/A_S01_matrix.mtx.gz` | 15.81 MB |
| `A/A_S02_barcodes.tsv.gz` | 4.3 KB |
| `A/A_S02_features.tsv.gz` | 333.4 KB |
| `A/A_S02_matrix.mtx.gz` | 4.66 MB |
| `A/A_S03_barcodes.tsv.gz` | 25.0 KB |
| `A/A_S03_features.tsv.gz` | 333.4 KB |
| `A/A_S03_matrix.mtx.gz` | 39.09 MB |
| `A/A_S04_barcodes.tsv.gz` | 21.9 KB |
| `A/A_S04_features.tsv.gz` | 333.4 KB |
| `A/A_S04_matrix.mtx.gz` | 28.53 MB |
| `A/A_S05_barcodes.tsv.gz` | 48.2 KB |
| `A/A_S05_features.tsv.gz` | 333.4 KB |
| `A/A_S05_matrix.mtx.gz` | 78.41 MB |
| `A/A_S06_barcodes.tsv.gz` | 2.5 KB |
| `A/A_S06_features.tsv.gz` | 333.4 KB |
| `A/A_S06_matrix.mtx.gz` | 2.44 MB |
| `A/A_S07_barcodes.tsv.gz` | 17.4 KB |
| `A/A_S07_features.tsv.gz` | 333.4 KB |
| `A/A_S07_matrix.mtx.gz` | 16.88 MB |
| `A/A_S08_barcodes.tsv.gz` | 7.7 KB |
| `A/A_S08_features.tsv.gz` | 333.4 KB |
| `A/A_S08_matrix.mtx.gz` | 6.07 MB |
| `A/A_S09_barcodes.tsv.gz` | 19.5 KB |
| `A/A_S09_features.tsv.gz` | 333.4 KB |
| `A/A_S09_matrix.mtx.gz` | 27.44 MB |
| `A/A_S10_barcodes.tsv.gz` | 17.2 KB |
| `A/A_S10_features.tsv.gz` | 333.4 KB |
| `A/A_S10_matrix.mtx.gz` | 23.68 MB |
| `A/A_S11_barcodes.tsv.gz` | 43.9 KB |
| `A/A_S11_features.tsv.gz` | 333.4 KB |
| `A/A_S11_matrix.mtx.gz` | 62.80 MB |
| `A/A_S12_barcodes.tsv.gz` | 41.7 KB |
| `A/A_S12_features.tsv.gz` | 333.4 KB |
| `A/A_S12_matrix.mtx.gz` | 66.50 MB |
| `A/sample_metadata.csv` | 1.5 KB |
| `B/B_S01_filtered_feature_bc_matrix.h5` | 18.83 MB |
| `B/B_S02_filtered_feature_bc_matrix.h5` | 362.0 KB |
| `B/B_S03_filtered_feature_bc_matrix.h5` | 12.18 MB |
| `B/B_S04_filtered_feature_bc_matrix.h5` | 367.5 KB |
| `B/B_S05_filtered_feature_bc_matrix.h5` | 15.20 MB |
| `B/B_S06_filtered_feature_bc_matrix.h5` | 14.83 MB |
| `B/B_S07_filtered_feature_bc_matrix.h5` | 13.14 MB |
| `B/B_S08_filtered_feature_bc_matrix.h5` | 13.57 MB |
| `B/B_S09_filtered_feature_bc_matrix.h5` | 19.43 MB |
| `B/B_S10_filtered_feature_bc_matrix.h5` | 24.65 MB |
| `B/B_S11_filtered_feature_bc_matrix.h5` | 18.20 MB |
| `B/B_S12_filtered_feature_bc_matrix.h5` | 18.33 MB |
| `B/sample_metadata.csv` | 0.9 KB |
| `C/C_S01_barcodes.tsv.gz` | 53.0 KB |
| `C/C_S01_features.tsv.gz` | 333.4 KB |
| `C/C_S01_matrix.mtx.gz` | 73.40 MB |
| `C/C_S02_barcodes.tsv.gz` | 72.6 KB |
| `C/C_S02_features.tsv.gz` | 333.4 KB |
| `C/C_S02_matrix.mtx.gz` | 79.41 MB |
| `C/C_S03_barcodes.tsv.gz` | 160.5 KB |
| `C/C_S03_features.tsv.gz` | 333.4 KB |
| `C/C_S03_matrix.mtx.gz` | 104.58 MB |
| `C/C_S04_barcodes.tsv.gz` | 74.7 KB |
| `C/C_S04_features.tsv.gz` | 333.4 KB |
| `C/C_S04_matrix.mtx.gz` | 96.82 MB |
| `C/C_S05_barcodes.tsv.gz` | 85.5 KB |
| `C/C_S05_features.tsv.gz` | 333.4 KB |
| `C/C_S05_matrix.mtx.gz` | 67.11 MB |
| `C/C_S06_barcodes.tsv.gz` | 15.2 KB |
| `C/C_S06_features.tsv.gz` | 333.4 KB |
| `C/C_S06_matrix.mtx.gz` | 28.73 MB |
| `C/C_S07_barcodes.tsv.gz` | 75.2 KB |
| `C/C_S07_features.tsv.gz` | 333.4 KB |
| `C/C_S07_matrix.mtx.gz` | 74.47 MB |
| `C/C_S08_barcodes.tsv.gz` | 97.1 KB |
| `C/C_S08_features.tsv.gz` | 333.4 KB |
| `C/C_S08_matrix.mtx.gz` | 97.32 MB |
| `C/C_S09_barcodes.tsv.gz` | 41.5 KB |
| `C/C_S09_features.tsv.gz` | 333.4 KB |
| `C/C_S09_matrix.mtx.gz` | 44.78 MB |
| `C/C_S10_barcodes.tsv.gz` | 54.4 KB |
| `C/C_S10_features.tsv.gz` | 333.4 KB |
| `C/C_S10_matrix.mtx.gz` | 60.59 MB |
| `C/C_S11_barcodes.tsv.gz` | 122.9 KB |
| `C/C_S11_features.tsv.gz` | 333.4 KB |
| `C/C_S11_matrix.mtx.gz` | 118.68 MB |
| `C/C_S12_barcodes.tsv.gz` | 53.6 KB |
| `C/C_S12_features.tsv.gz` | 333.4 KB |
| `C/C_S12_matrix.mtx.gz` | 57.87 MB |
| `C/sample_metadata.csv` | 1.5 KB |
| `D/expression_log2.tsv.gz` | 3.96 MB |
| `D/sample_metadata.csv` | 2.1 KB |
| `D_key/condition_key.csv` | 0.3 KB |
| `E/protein_group_matrix.tsv.gz` | 489.4 KB |
| `E/sample_metadata.csv` | 0.9 KB |
| `V/expression_probe_matrix.tsv.gz` | 274.6 KB |
| `V/probe_annotation.tsv.gz` | 4.3 KB |
| `V/sample_metadata.csv` | 3.4 KB |
