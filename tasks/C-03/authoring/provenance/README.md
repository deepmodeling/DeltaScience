# 结构与协议来源

C-03 uses the exact shared BCL receptor assets described in structure_manifest.json. Chemical identity sources and original experimental panels are recorded in literature_sources.md and public literature_controls.json. raw/ contains only used crystallographic/CCD sources. Rejected alternative structures and development logs are excluded.

6O0K is a soluble engineered BCL2/BCLXL-loop construct; 4QVX is an engineered/truncated soluble BCLXL construct. They are not full-length membrane proteins. BCL2 ASP35 lacks CG/OD1/OD2 in the deposited coordinates; the deterministic local-frame completion is recorded in structure_manifest.json and prepare_assets.py, more than21A from the native ligand. All observed protein heavy-atom coordinates are retained. Native ligand bond orders and stereochemistry are assigned from the matching official CCD templates.

The computational baseline is navitoclax (4LVT CCD1XJ identity); its4LVT coordinates are not used in either docking frame. Geometry references are venetoclax/6O0K and A-1155463/4QVX. A-1331852 is a distinct literature control, not the4QVX ligand. No experimental fold selectivity is inferred from docking.

Protocol0.1.0 retains C02 docking and portfolio architecture, changes the target direction, replaces PARP anchors with a fixed native-site contact proxy, uses a broad BCL property envelope, reports QED/ESOL/alerts/strain, canonicalizes atom order before preparation, and fixes specified-stereochemistry matching in the independent reference workflow. The D1/D2/I acceptance rules remain fixed and unchanged; outstanding independent calibration is explicitly recorded in ../validation_status.json. Reference solution status is MISSING. No passing portfolio, executable reference/search program, candidate results or search logs are included.

See structure_notes.md for construct details and portable rebuild instructions. build_assets.sh writes only to the chosen output directory and does not modify frozen task inputs.
