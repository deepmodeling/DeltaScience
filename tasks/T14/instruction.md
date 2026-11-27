Design a frustrated amorphous trap network by jointly choosing 504 binary trap orientations and 72 continuous processing controls to maximize selective release yield (species A release fraction multiplied by species B retention fraction), especially the worst-case yield across all nodes, four intervention families (thermal, flux, isotope, cyclic), and both forward/reverse processing histories.

Inputs in `/workspace/resources/`:
- `network.json`: nonperiodic interaction network, site properties, motif/loop contacts, processing-zone couplings, and physical coefficients.
- `model.md`: constitutive equations, uncertainty envelope, and conventions.
- `forward.py`: NumPy-based O(n) forward evaluator.
- `calibration.json`: 48 calibration scenarios (12 per intervention family; exchangeable samples from the full uncertainty envelope).

Hard design constraints:
- 504 binary orientations in {-1, +1} partitioned into three chemical inventory classes of 168 sites each; each class must contain exactly 84 positive (+1) orientations.
- 24 processing zones with per-zone bounds: `anneal_temperature_K` in [650, 850] K, `dwell_hours` in [0.5, 1.5] hours, `quench_K_per_s` in [5, 25] K/s.
- Total budgets across the 24 zones: sum(anneal_temperature_K) <= 24 * 750 K, sum(dwell_hours) <= 24 * 1.0 h, sum(quench_K_per_s) <= 24 * 15 K/s.
- All four intervention families and both histories are evaluated on the exact same single design. Note that global sign inversion of all 504 orientations is a gauge symmetry, whereas partial flips or node permutations are not.

Deliverable:
Write `/workspace/outputs/design.json` (regular file <= 2 MiB) containing four JSON arrays in the supplied index order:
- `orientation`: 504 integers in {-1, +1}
- `anneal_temperature_K`: 24 finite floats (K)
- `dwell_hours`: 24 finite floats (hours)
- `quench_K_per_s`: 24 finite floats (K/s)

Python 3.12 with NumPy and SciPy is installed. Time limit: 1 hour (4 CPUs, 8 GiB RAM, offline). Do not cheat or use external task-specific solutions.
