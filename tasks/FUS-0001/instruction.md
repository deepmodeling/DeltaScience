Improve a static axisymmetric free-boundary Grad-Shafranov equilibrium solver under fixed physical inputs to reduce the 95th-percentile core plasma-boundary discrepancy against the reference equilibrium across all 212 time slices of a tokamak discharge.

Inputs in `/root` (`TF_PUBLIC_DIR`):
- `cases.npz`: physical inputs for all 212 time slices (`case_id`, time, Ip, fvac, Lao profile coefficients and edge flags, 64 conductor names and currents). Load with `numpy.load(path, allow_pickle=False)`.
- `case-schema.md`, `paper_geometry.py`, `resource.json`, `dependency-snapshot.json`: conductor mapping, output grid definition, frozen separatrix diagnostic, and environment details.

Fixed physical constraints:
- Keep the machine geometry, active-coil and 150 passive-structure definitions/currents, Lao profile parameters, Ip normalization, and fvac strictly unchanged. Do not omit or substitute time slices, and do not refit physical inputs or look up reference outputs.
- Output total poloidal magnetic flux in Wb (note: solvers using Wb/(2*pi) must multiply by 2*pi) on the 65x65 grid R in [0.06, 2.0] m, Z in [-2.2, 2.2] m with axes (sample, R, Z).
- You may improve the nonlinear solver, initialization, discretization, or internal boundary handling using any valid forward equilibrium method.

Evaluation metric:
- For each time slice, the frozen separatrix diagnostic extracts 360 poloidal-angle core boundary points (excluding divertor legs) and computes the maximum directional Euclidean deviation zeta.
- The overall error E is the linear 95th percentile across the 212 sorted zeta values (E = 0.55*z_200 + 0.45*z_201).
- Continuous score scales from 0.20 at baseline E0 = 35.109 mm to 1.00 at E <= 30.0 mm (and 0.00 at E >= 50.0 mm).

Deliverables in `/root/outputs/submission/`:
1. `flux.npz` containing only `case_id` (212 unique Unicode strings) and `psi_Wb` (finite float array of shape (212, 65, 65), uncompressed archive members <= 32 MB).
2. `solve.py` or `solve.sh`: reproducible solver script that generates `flux.npz` from `/root/cases.npz`.
3. `method.md`: concise technical description of your numerical method.

Python environment: `/opt/challenge-runtime/mastu` (Python 3.12, NumPy, SciPy, freegs4e, Shapely, Numba, h5py). Time limit: 4 hours (2 CPUs, 4 GiB RAM).
