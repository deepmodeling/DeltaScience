# Frozen BCL2/BCLXL structure assets

Prepared on 2026-10-30 for the C-03/C-04 benchmark authoring workspace. These are crystallographic soluble constructs. They must not be described as full-length, completely native wild-type proteins. No docking, score calibration, candidate search or backbone relaxation was performed.

## Prepared inputs

| Role | Source | Files in `prepared/` |
|---|---|---|
| BCL2 rigid receptor | 6O0K chain A | `bcl2_6o0k_chainA_protein.pdb`, `bcl2_6o0k_chainA.pdbqt` |
| BCL2 site reference | 6O0K, LBM A301, complete alternate A, venetoclax | `site_reference_venetoclax_6o0k_chainA.sdf` |
| BCLXL rigid receptor | 4QVX chain A | `bclxl_4qvx_chainA_protein.pdb`, `bclxl_4qvx_chainA.pdbqt` |
| BCLXL site reference | 4QVX, 3CQ A301, A-1155463 | `site_reference_a1155463_4qvx_chainA.sdf` |
| Shared baseline chemical identity | 4LVT, 1XJ A301, navitoclax | `navitoclax_4lvt_chainA_experimental.sdf` |

The navitoclax SDF contains a true experimental 4LVT pose and the intended stereoisomer, but those coordinates are **not** in either prepared receptor frame. Its graph/SMILES can define the shared baseline for independent scoring on both receptors. The two `site_reference_*` files define the crystallographic binding sites and geometric controls in their own receptor frames. Do not use the 4LVT navitoclax coordinates as a native pose in 6O0K or 4QVX. No navitoclax pose transfer was attempted because the task schema permits separate chemical and geometric references.

The exact baseline SMILES and molecular identities are in `structure_manifest.json`. Native reference molecular weights are approximately 868.46 Da (venetoclax) and 669.80 Da (A-1155463); navitoclax is approximately 974.63 Da. Small-molecule bounds inherited from a PARP template therefore require task-specific authoring choices.

## Protein construct and preparation boundaries

**6O0K:** 1.62 Angstrom human BCL2-derived soluble construct. The deposited DBREF explicitly maps A35–A91 to human BCLXL (Q07817), with BCL2 sequence on either side. Chain A observed residues are 9–35 and 90–203. The PDB missing-residue list includes A1–8, A77–89 and A204–207. No absent loop or terminal backbone was modeled. All selected observed heavy atoms retain their exact deposited coordinates. Alternate locations are selected consistently as blank/A for the whole protein and ligand. The only missing heavy-atom repair is ASP A35 CG/OD1/OD2, over 21 Angstrom from the native ligand at its closest observed atom. The repair grafts an observed ASP A103 sidechain into the recipient N/CA/CB local frame, deterministically rotates around CA–CB to avoid overlaps, and adds just the three absent atoms. The donor, rotation, coordinates and clash check are recorded in the manifest. Reconstructed atoms are modeling inputs, not experimental observations.

**4QVX:** 2.10 Angstrom human BCLXL-derived soluble construct. The deposited structure includes a deleted loop/linker and tag annotations. Its observed chain A residues are 2–22 and 82–196. Deposited SEQADV records mark LYS158 vs UniProt GLU158 and ALA189 vs UniProt ASP189 as `CONFLICT`; the structure is retained exactly as deposited rather than silently relabeled or mutated. Their minimum native-ligand heavy-atom distances are recorded in the manifest. The complete protein heavy-atom set needs no sidechain reconstruction. Residues and numbering must be interpreted in the deposited construct frame, not inferred from a full-length numbering assumption.

For each receptor only chain A protein ATOM records are kept. Other chains, waters, native ligand, buffers and ions are excluded from the rigid protein. The native ligand is retained separately. Meeko 0.8.0 standard residue templates add hydrogens and use template Gasteiger charges; no `delete_bad_res`, residue deletion, `forgive_extra_bonds`, flexible residue or minimization option was used. Template protonation is a frozen computational preparation choice, not an experimentally measured protonation assignment.

## Site definition and checks

Each fixed pocket is the set of chain A residues with at least one protein heavy atom within 4.5 Angstrom of that receptor's native ligand heavy atoms. The lists are recorded in the manifest. Protein atoms outside the pocket remain in the rigid receptor. Search boxes are centered on the native ligand axis-aligned bounding-box midpoint. Each box dimension is the ligand span plus 10 Angstrom, with a minimum of 32 Angstrom:

| Receptor | Center (Angstrom) | Size (Angstrom) |
|---|---|---|
| BCL2 / 6O0K | -14.226, 1.146, -10.800 | 32, 32, 32 |
| BCLXL / 4QVX | -20.152, 6.010, 6.544 | 32, 32, 32 |

Structure preparation was independently read back before packaging. All 1172 selected observed BCL2 heavy atoms were preserved and 3 explicitly reconstructed atoms added; all 1093 selected observed BCLXL heavy atoms were preserved. PDBQT preparation preserves every prepared protein heavy atom and coordinate exactly. CCD atom-name mapping supplies ligand bond orders and formal charges, with graph identity independently checked against official ideal SDF InChIKeys. All native ligand heavy coordinates are preserved. Minimum native heavy-atom van der Waals gaps are -0.298 Angstrom (BCL2) and -0.327 Angstrom (BCLXL), using radii C1.70/N1.55/O1.52/S1.80/F1.47/Cl1.75. This verifies basic input consistency; it is not a docked baseline, verifier pass, selectivity prediction or complete scientific validation.

## Sources

Raw source files are kept under `raw/` with SHA-256 hashes in `structure_manifest.json`.

- [PDB 6O0K](https://www.rcsb.org/structure/6O0K), [downloaded PDB](https://files.rcsb.org/download/6O0K.pdb); Birkinshaw et al., *Structures of BCL-2 in complex with venetoclax reveal the molecular basis of resistance mutations*, Nat Commun 2019, [doi:10.1038/s41467-019-10363-1](https://doi.org/10.1038/s41467-019-10363-1).
- [PDB 4QVX](https://www.rcsb.org/structure/4QVX), [downloaded PDB](https://files.rcsb.org/download/4QVX.pdb); Tao et al., *Discovery of a Potent and Selective BCL-XL Inhibitor with in Vivo Activity*, ACS Med Chem Lett 2014, [doi:10.1021/ml5001867](https://doi.org/10.1021/ml5001867).
- [PDB 4LVT](https://www.rcsb.org/structure/4LVT), [downloaded PDB](https://files.rcsb.org/download/4LVT.pdb); Souers et al., *ABT-199, a potent and selective BCL-2 inhibitor, achieves antitumor activity while sparing platelets*, Nat Med 2013, [doi:10.1038/nm.3048](https://doi.org/10.1038/nm.3048). This engineered BCL2 construct includes an A4P mutation at an unresolved N-terminal site and is used only for navitoclax chemical identity/coordinate provenance here.
- Official CCD atom/bond definitions: [LBM](https://files.rcsb.org/ligands/download/LBM.cif), [3CQ](https://files.rcsb.org/ligands/download/3CQ.cif), [1XJ](https://files.rcsb.org/ligands/download/1XJ.cif), with corresponding `{ID}_ideal.sdf` downloads. 3CQ is A-1155463, not A-1331852. No A-1331852 crystal pose is claimed or included.

## Reproduction

From an environment containing the pinned chemistry tools, run `bash authoring/provenance/build_assets.sh /tmp/bcl-assets-rebuilt`. Python defaults to `python3`; set BCL_ASSET_PYTHON to select another executable. The script uses only raw files beside itself, writes extracted/rebuilt assets into the chosen output directory, and prepares receptors with Meeko0.8.0. It does not overwrite frozen public inputs and never performs docking. Runtime images use Python3.11; the author's structure extraction was checked using Python3.12 and the same pinned chemistry-library versions. Hash equality, not a local interpreter path, defines the frozen assets.

The verifier contact mask is the **atom subset**, rather than every atom of the residue lists summarized above. Its exact target-specific atom identifiers and coordinates are frozen in public protocol.json.
