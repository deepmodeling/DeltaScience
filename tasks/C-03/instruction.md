Starting from navitoclax, design a portfolio of 3 to 25 small molecules so that at least three distinct molecules retain BCL2 binding affinity while weakening BCL-XL (BCL2L1) binding affinity relative to navitoclax under independent multi-seed docking.

Inputs and references in `/app/inputs`:
- `task_spec.md`, `protocol.json`, and `completion_rules.md`: full docking protocol, property gates, and completion rules.
- Prepared receptor structures for BCL2 (6O0K chain A) and BCL-XL (4QVX chain A), native site-reference poses (venetoclax for BCL2, A-1155463 for BCL-XL), and literature controls.

Target criteria (navitoclax is the scoring reference):
- Docking uses three independent AutoDock Vina searches per receptor (seeds 42, 137, 2026), taking the lowest mode-1 energy per receptor.
- Define D1 = E_BCL2(candidate) - E_BCL2(navitoclax), D2 = E_BCLXL(candidate) - E_BCLXL(navitoclax), and I = D2 - D1 (in kcal/mol).
- Target thresholds for full credit per qualifying molecule: D1 <= 0.50, D2 >= 1.00, I >= 1.50, along with the molecular property gates, BH3-site contact/box/clash checks, and submitted-to-selected BCL2 pose RMSD <= 2.0 A.
- Portfolio diversity: the selected trio of non-duplicate molecules must span at least two chirality-free Murcko scaffolds and have pairwise Morgan (radius 2, 2048-bit) Tanimoto similarity <= 0.85.

Deliverables (only these two files are transferred to the verifier):
1. `/workspace/solution.json` containing `"target": "BCL2"`, `"counter_target": "BCLXL"`, and `"molecules"` (an array of 3 to 25 SMILES strings).
2. `/workspace/poses_bcl2.sdf` containing exactly one 3D pose per listed molecule in the 6O0K receptor frame, in matching order, with `CANDIDATE_INDEX` set to its 1-based index.

You can validate a draft workspace before publishing via:
```bash
python /app/completion/check.py --workspace /workspace/drafts/round-1 --report /workspace/checks/round-1-full.json --publish /workspace
```
Time limit: 5 hours. Do not use external solutions or hints specific to this task.
