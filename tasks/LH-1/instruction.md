Design a compact quasi-axisymmetric (QA) stellarator plasma boundary with field-period number nfp = 2 starting from the circular-cross-section torus in `/app/seed.json`. Your goal is to reduce the aspect ratio A to at most 6.0 while simultaneously satisfying all magnetic-confinement and particle-transport constraints below.

Environment and inputs:
- `/app/seed.json`: initial circular torus boundary.
- `/app/input.vmec`, `/app/case.json`, `/app/physics.py`, `/app/evaluate.py`: fixed-boundary zero-beta zero-net-current VMEC template, numerical configuration, physics routines, and local evaluator.
- Available tools: `xvmec2000`, `simsopt`, `booz_xform`, `NEO`, and `SIMPLE`.

Physical conventions and target constraints:
- Stellarator-symmetric boundary with nfp = 2; effective minor radius normalized to 1.70 m; on-axis Boozer field B00 normalized to 5.70 T for particle tracing.
- Aspect ratio: A <= 6.0.
- 41-surface quasi-axisymmetry residual Q (helicity (1, 0), s = 0, 0.025, ..., 1 with weight 10 at s = 0.25 and 1 elsewhere): Q <= 3.2e-6.
- Mean rotational transform: within 1% relative deviation of 0.42.
- Endpoint vacuum magnetic well (V'(0) - V'(1)) / V'(0): >= 0.0048.
- Maximum effective ripple across the four surfaces closest to s = 0.2, 0.4, 0.6, 0.8: <= 0.0022%.
- Collisionless 3.5 MeV alpha-particle losses plus unresolved orbits (4096 particles launched at s = 0.25, traced for 0.2 s): <= 1.

Deliverable:
Write only `/app/boundary.json` (UTF-8 JSON) specifying the Fourier modes:
  R(theta, phi) = sum rbc(m, n) cos(m*theta - n*nfp*phi)
  Z(theta, phi) = sum zbs(m, n) sin(m*theta - n*nfp*phi)
with integer m >= 0 (n >= 0 when m = 0), unique (m, n) pairs, finite real coefficients, rbc(0, 0) > 0, and zbs(0, 0) = 0. Format:
```json
{"nfp": 2, "modes": [{"m": 0, "n": 0, "rbc": 1.0, "zbs": 0.0}]}
```

You may add higher-order Fourier modes and use any optimization method locally. To test a candidate boundary, run:
```bash
python /app/evaluate.py --submission /app/boundary.json --output /work/evaluation
```
Use a fresh output directory for each evaluation. Work offline with the installed physics tools; do not fetch pre-optimized boundaries or external solution scripts. Time limit: 24 hours (24 CPUs, 64 GiB RAM).
