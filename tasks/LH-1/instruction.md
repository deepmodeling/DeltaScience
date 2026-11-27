Compact Quasi-Axisymmetric Stellarator Boundary Optimization

Can a three-dimensional magnetic confinement cage be made more compact while still giving particles an approximately axisymmetric magnetic field strength profile? Starting from a simple circular-cross-section torus, optimize the outer plasma boundary to reduce the aspect ratio A as much as possible while preserving quasi-axisymmetry, magnetic well, rotational transform, effective ripple, and energetic-particle confinement.

Submit only `/app/boundary.json`. All physical metrics are independently recomputed by the evaluator.

1. Scientific Motivation

The aspect ratio A is the ratio of the major radius to the minor radius of the torus. In this task, the effective minor radius is normalized to 1.70 m, so a smaller A corresponds to a tighter, more compact torus.

Reducing the aspect ratio simultaneously perturbs the magnetic field strength spectrum, field-line twist, and particle drifts. Quasi-axisymmetry suppresses outward radial drift, but making the boundary more compact still requires verifying transport metrics and collisionless particle orbits. Your objective is to find a compact boundary that satisfies all confinement criteria below.

2. Fixed Conditions and Performance Requirements

The starting point `/app/seed.json` is a circular-cross-section torus. The environment also provides the VMEC template `/app/input.vmec`, physics routines, and the public evaluator. Starting from this initial geometry, adjust the 3D Fourier boundary modes, solve the equilibrium, and evaluate candidate designs.

Fixed conditions:
- Field periods: nfp = 2, stellarator-symmetric boundary
- Equilibrium model: fixed-boundary, zero pressure, zero net enclosed toroidal current everywhere
- Scale and particle-tracing field strength: effective minor radius 1.70 m, on-axis Boozer B00 = 5.70 T
- Degrees of freedom: Fourier coefficients describing the plasma boundary; additional higher-order modes may be added

Target constraints (aspect ratio A <= 6.0 and all five constraints below must be satisfied simultaneously):
- 41-surface quasi-axisymmetry residual Q: <= 3.2e-6 (maintains small symmetry error from core to edge)
- Mean rotational transform: within 1% relative deviation of 0.42 (maintains field-line twist)
- Endpoint vacuum magnetic well: >= 0.0048 (maintains favorable volume-derivative profile)
- Maximum effective ripple across four surfaces: <= 0.0022% (controls low-collisionality neoclassical transport)
- Sum of alpha-particle losses and unresolved orbits: at most 1 out of 4096 trajectories over 0.2 s tracing

3. Describing the Final Design in JSON

Submit only `/app/boundary.json` as UTF-8 JSON. Example format (illustrative only; the complete starting geometry is in `/app/seed.json`):

```json
{"nfp": 2, "modes": [
  {"m": 0, "n": 0, "rbc": 1.0, "zbs": 0.0},
  {"m": 1, "n": 0, "rbc": 0.2, "zbs": 0.2}
]}
```

Each mode specifies integers m, n and finite real numbers rbc, zbs representing:

```text
R(theta, phi) = sum rbc(m, n) cos(m*theta - n*nfp*phi)
Z(theta, phi) = sum zbs(m, n) sin(m*theta - n*nfp*phi)
```

Requirements: m >= 0; when m = 0, use n >= 0. Unlisted modes are zero; mode ordering is arbitrary; zbs(0, 0) = 0. All length coefficients share the same unit, and the overall scale is normalized by the evaluator to an effective minor radius of 1.70 m. Each (m, n) pair may appear at most once, with rbc(0, 0) > 0.

You may add higher-order modes and choose any optimization method. Do not submit optimization history, search scripts, or self-reported physical metrics.

4. Evaluation and Thresholds

Each metric is checked against the reference thresholds in `/app/case.json`:
- Upper-bound metrics: value <= reference.
- Lower-bound metrics: value >= reference.
- Target-matching metrics: abs(value - reference) <= width (mean rotational transform target 0.42 with 1% relative tolerance).
- Alpha-particle metric: confirmed losses plus unresolved orbits <= 1 (out of 4096 trajectories).

All thresholds and inequalities are enforced strictly; only a 1e-12 relative floating-point rounding tolerance is allowed at boundaries. Missing submissions, malformed JSON, or failed physics evaluations receive 0 with a diagnostic reason; environment errors are reported separately.

5. Getting Started and Resources

The environment provides `/app/physics.py`, `/app/evaluate.py`, and numerical configuration `/app/case.json`. Copy the seed geometry and run the local evaluator:

```bash
cp /app/seed.json /app/boundary.json
python /app/evaluate.py --submission /app/boundary.json --output /work/evaluation
```

`/work/evaluation/result.json` reports the primary objective, per-constraint pass status, and evaluation score. Use a fresh output directory for each evaluation. Official grading recomputes all quantities from `/app/boundary.json` using the exact same code and parameters.

This task is solved offline. You may use the installed physics codes, optimization libraries, local documentation, and general examples. Do not access the internet to retrieve pre-optimized boundaries, coils, or task-specific optimization scripts.

Resources: 24 CPU cores, 64 GiB RAM, no GPU; solving budget 24 hours; single evaluation limit 12 hours.

To solve equilibria directly during search, invoke `xvmec2000` and inspect results via `simsopt.mhd.Vmec(wout_path)`. Lower-cost proxy calculations may be used during intermediate search stages.

6. Physics Evaluation Pipeline

Given a submitted boundary, the evaluator first rescales the effective minor radius to 1.70 m and solves the vacuum equilibrium with VMEC. Aspect ratio A is taken from VMEC `aspect`, and mean rotational transform is taken from `Vmec.mean_iota()` on the uniform half-flux grid.

Quasi-axisymmetry is evaluated from the magnetic axis (s = 0) to the boundary (s = 1) using SIMSOPT `QuasisymmetryRatioResidual` with helicity `(helicity_m, helicity_n) = (1, 0)` across 41 flux surfaces s = 0, 0.025, ..., 1, weighted by 10 at s = 0.25 and 1 on all other surfaces.

The vacuum magnetic well is defined from V' = dV/ds as `W = (V'(0) - V'(1)) / V'(0)` via `Vmec.vacuum_well()`. The equilibrium is then transformed to Boozer coordinates using `booz_xform`, and NEO computes the effective ripple `eps_eff = EPSTOT^(2/3)` on the four flux surfaces closest to s = 0.2, 0.4, 0.6, and 0.8, taking the maximum across the four surfaces.

Finally, after normalizing the on-axis Boozer zero mode B00 to 5.70 T, SIMPLE launches 4096 collisionless 3.5 MeV alpha particles from a thin shell at s = 0.25 (volume-sampled in space, isotropic in velocity) and traces guiding-center orbits for 0.2 s. Any trajectory crossing s = 1 or failing numerical integration is counted as unconfinable.

Grid resolutions, fixed sampling, and solver tolerances are documented in `/app/case.json`, `/app/input.vmec`, and `/app/physics.py`. When higher-order Fourier modes are submitted, the evaluator increases numerical resolution accordingly.
