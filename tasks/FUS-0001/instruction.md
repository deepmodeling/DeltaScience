Numerical compatibility of MAST-U free-boundary equilibria at fixed physical inputs

Research background

A tokamak uses magnetic fields to confine a hot plasma. Analysing a discharge, studying plasma shape, or building a control model requires knowledge of the magnetic field and current distribution, as well as the plasma boundary. These quantities are coupled through a magnetohydrodynamic equilibrium model. Under axisymmetry, the Grad–Shafranov equation is commonly used to describe that equilibrium.

Magnetic probes and flux loops provide local magnetic-field and flux information; they do not directly reveal the entire plasma boundary. Magnetic equilibrium reconstruction combines these measurements with a physical model to estimate currents, profiles and boundaries consistent with the observations. Sensor numbers, positions and installation space are limited, while measurement noise, channel anomalies and passive vessel currents can affect reconstruction. Assessing magnetic diagnostics therefore also requires reliable equilibrium calculations, so that diagnostic-information effects can be distinguished from numerical-implementation effects.

Two related steps must be distinguished. A reconstruction problem estimates physical inputs and equilibrium from measurements. A forward equilibrium problem calculates the equilibrium when machine geometry, conductor currents and plasma profiles are already specified. This task studies the latter. It does not ask you to redesign a sensor array. It asks why different equilibrium implementations can return different plasma boundaries at identical physical inputs, and whether numerical-method improvements can reduce those differences.

This matters when equilibrium results are used downstream. Magnetically reconstructed equilibria support discharge-scenario analysis, shape-control models and other calculations. If changing equilibrium software also changes the geometry, downstream comparisons mix physical differences with implementation differences. Reducing such discrepancies in a fixed physical scenario improves the consistency and comparability of results across codes.

Prior research and remaining difficulties

Pentland et al., *Physica Scripta* 100 (2025) 025608, study this issue for MAST-U. They extract active-coil and passive-structure currents and plasma-profile inputs from EFIT++ magnetic reconstructions, then use FreeGSNKE and Fiesta to solve static free-boundary equilibria. Here, “free-boundary” means that the plasma boundary is determined by the calculation rather than prescribed as a fixed curve. The paper considers conventional-divertor shot45425 and Super-X shot45292; this task uses the45425 branch.

Even with identical inputs and stopping tolerances of the same order, numerical treatments of passive conductors, the plasma core and boundary can produce differences. Some early time slices can also have different valid equilibrium branches. Merely tightening an iteration tolerance therefore does not guarantee closer agreement with the specified reference branch. The challenge concerns the actual performance of numerical methods for the same physical problem.

The official archived FreeGSNKE final fields form the baseline, and the corresponding EFIT++ results provide the evaluation reference. The paper reports that approximately95% of cases have a maximum corresponding core-boundary distance below3.5cm. Re-evaluating the original212 archived cases with the task's fixed diagnostic gives201/212 passing cases (94.8113%, rounding to95%). The task's linear95th-percentile value is 0.035109356870013486m.

The objective is numerical compatibility with the EFIT++ reference branch. EFIT++ is itself a reconstruction, not an independently measured true equilibrium. Smaller discrepancies therefore do not establish improved accuracy relative to experimental truth. This distinction limits the conclusions that may be drawn from this task.

Task and scientific scope

Improve a static free-boundary equilibrium method to reduce the95th-percentile boundary discrepancy at identical physical inputs. Nonlinear solution methods, initialization, discretization and internal boundary identification may be studied or combined; the frozen scoring diagnostic must not be changed. A novel algorithm is not required. Submit complete magnetic-flux fields and inspectable method code.

Scientific value and interpretation

Studies of magnetic-diagnostic layouts, coil designs and control models use equilibrium calculations to generate training or validation equilibria and compare plasma shapes across designs. If switching equilibrium software changes the boundary without changing the physical inputs, the resulting geometry differences can become mixed with design differences. Section6 of Pentland et al. explicitly connects validated equilibrium solvers with equilibrium libraries and coil or magnetic-diagnostic position optimisation.

This task addresses a directly testable part of that workflow: reducing core-boundary discrepancies when the physical inputs reconstructed for the same discharge are passed from EFIT++ to a forward solver. For example, unchanged coil currents and profiles can yield different calculated boundaries because of implementation differences. Reducing that change reduces geometric inconsistency when these cases are used across codes; the change must not be mistaken for an effect of modifying coils or diagnostic layouts. The evaluator measures this improvement with the same original boundary diagnostic.

The scientific value is improved transfer of equilibrium results between codes in the paper's scenario, supplying more geometrically consistent inputs for subsequent design comparisons or model use. A decrease in E directly establishes reduced boundary discrepancy relative to the reference branch for these fixed cases. It does not by itself establish a better sensor layout, greater experimental reconstruction accuracy, or improved downstream control performance. Those further uses require their own validation and are not claimed as achieved outcomes here.

Public files are under `/root`; `TF_PUBLIC_DIR` points to that directory. Input and resource filenames below are relative to it.

Fixed paper conditions

- Use the archived MAST-U machine description with asymmetric active coils. Keep active-coil and150 passive-structure geometry and associated currents fixed. Passive currents follow the20 current groups and cross-sectional area allocation. Do not set vessel currents to zero or tune P6/other coil currents to match the reference.
- Keep the section4.3 Lao profile alpha/beta coefficients, edge logicals, original Ip normalization and fvac. Refitting physical parameters is not a numerical-method improvement in this task.
- Return the65×65 grid R∈[0.06,2.0]m, Z∈[-2.2,2.2]m with axes(R,Z). Use exactly the212 original cases `efit_times[8:-2]` listed in `cases.npz`; do not omit early, difficult or failed cases. Different internal numerical methods are allowed, but must preserve the physical problem and output grid.
- The published FreeGSNKE baseline uses Newton–Krylov, default O-point initialization and relative stopping tolerance1e-6. Paper equation3.6 concerns normalized successive-iteration flux change, not a1e-6 PDE residual. If using the paper iteration-change criterion, retain1e-6. For another criterion, explain and record its numerical correspondence to the original accuracy setting; do not conflate iteration change with PDE residual.
- Output total poloidal flux in Wb. FreeGSNKE internal flux and raw EFIT++ Wb/(2π) fields require multiplication by2π. Do not independently shift or rescale fields to improve the score.

Public resources and physical inputs

Public files are under `/root`, also identified by `TF_PUBLIC_DIR`. Official geometry, software and papers are available through `resource.json`. Networking for acquisition, installation and reading is allowed; no particular solver implementation is mandatory.

| File | Purpose |
| --- | --- |
| `cases.npz` | Physical inputs for all212 evaluation times; fields below |
| `case-schema.md` | Original conductor names, current mapping and output grid |
| `resource.json`, `resources.yaml` | Official sources, usage, versions, licensing and bundled status |
| `baseline-provenance.json` | Paper/data DOIs, archive hashes and baseline calibration provenance |
| `paper_geometry.py` | Public frozen contour diagnostic, not an equilibrium solver |
| `dependency-snapshot.json` | Preinstalled scientific libraries: ABI, pinned versions and sources |

Read `cases.npz` using `numpy.load(path, allow_pickle=False)`. Sample axes align with `case_id`; the current-matrix columns align with `conductor_names`.

| Field | Shape | Type and meaning |
| --- | --- | --- |
| `case_id` | `(212,)` | Unicode strings, unique evaluation-time identities |
| `time_s` | `(212,)` | float64, times in s |
| `Ip_A` | `(212,)` | float64, original plasma current in A |
| `fvac_Tm` | `(212,)` | float64, vacuum-field/reference-radius product in T·m |
| `alpha` | `(212,2)` | float64, original EFIT++ Lao pressure-derivative profile coefficients |
| `beta` | `(212,2)` | float64, original EFIT++ Lao poloidal-current-function profile coefficients |
| `alpha_logic` | `(212,)` | int32, pressure-profile edge logical |
| `beta_logic` | `(212,)` | int32, other-profile edge logical |
| `conductor_names` | `(64,)` | Unicode strings, original EFIT conductor names |
| `conductor_currents_A` | `(212,64)` | float64, corresponding original conductor currents in A |

Use the coefficient and logical conventions from paper section4.3 and the archived `extract_lao_profile_coefficients`. Do not replace normalisation or edge treatment. Conductor names are not preconverted FreeGSNKE circuit names. Apply the archived `build_currents_pickle` mapping for windings, polarity, and passive-current group/area allocation. Script defaults do not override this task's requirement to retain original nonzero passive currents.

Machine geometry and mapping scripts are in the official DOI archive's `data` and `freegsnke` directories. Public inputs contain no reference flux, magnetic axes, separatrices or other evaluation labels. These212 cases form the complete evaluation set; there are no additional hidden times. Evaluation-reference outputs are not solve inputs.

Permitted information and method requirements

The corresponding EFIT++ flux, separatrix, magnetic-axis and other target outputs are evaluation references. Do not use them as method inputs, training labels, lookup tables or per-case correction targets. Do not download reference outputs and resubmit them. Published baseline results may inform development, but the method must produce results from the declared physical inputs rather than returning stored answers by time. Method provenance and compliance are independently evaluated in the trace; they do not gate or alter the numerical reward below.

Numerical evaluation

At each case, use the reference EFIT++ magnetic axis as the common center and the archived `Separatrix` algorithm to obtain360 corresponding core-boundary points by geometric poloidal angle, excluding divertor legs. Keep its X-point direction handling and isolated-point filtering unchanged with frozen diagnostic dependencies. The metric is the original maximum corresponding-point Euclidean distance, not Hausdorff distance or wall arclength:

\[
\zeta_j=\max_i\|\hat x_i-x_i\|_2.
\]

Valid-direction treatment follows the archived function: retain its isolated-point filter, exclude corresponding directions containing NaN in either boundary, and take the maximum over remaining directions. No comparable directions makes the result invalid. Every case must produce a finite zeta; all212 fields must be complete, finite and correctly formatted. An invalid submission receives numerical reward0 with a reason. Trusted-fixture, dependency and evaluator faults are platform failures without a scientific score.

Sort the212 distances as z₀,…,z₂₁₁. Fix linear quantile interpolation h=.95×211=200.45:

\[
E=0.55z_{200}+0.45z_{201}.
\]

The baseline metric is E₀=0.035109356870013486m, independently evaluated from the public paper artifacts under the fixed evaluation conditions. The linear-quantile aggregation is specified by this task; the paper reports a threshold-passing fraction. Report “approximately95% below3.5cm” separately from the linear95% quantile; they are not interchangeable metrics.

The numerical score depends only on E and submission validity. Matching the baseline earns0.2; worse valid results below5cm receive continuously lower credit, and E at or above5cm earns zero. Better-than-baseline results earn continuous optimization credit for reducing the error; a 95th-percentile distance of 30 mm or less receives full credit. The full-score target is a task scoring convention, not a proven attainable physical limit. The5cm zero-score line is a task scoring rule, not a theoretical bound from the paper. Report quality, credibility, and scientific-value judgments are assessed independently and do not change the verified metric score.

Submission files and data format

Write the following before the solve deadline:

```text
/root/outputs/submission/
├── flux.npz
├── solve.py or solve.sh
├── method.md
└── supporting code, parameters or model files, if needed
```

`flux.npz` must be a NumPy-readable data archive containing only:

| Field | Shape and requirements |
| --- | --- |
| `case_id` | `(212,)`, Unicode strings; exactly the public identities, without missing, duplicate or extra cases |
| `psi_Wb` | `(212,65,65)`, finite floating-point values; case, R, Z axes |

Rows may be reordered; the evaluator aligns by case_id. Grid axes are `np.linspace(0.06,2.0,65)` and `np.linspace(-2.2,2.2,65)`, using `meshgrid(indexing="ij")`. Submit total flux in Wb; convert internal Wb/(2π) fields first.

The NPZ must contain exactly two array members with combined uncompressed size at most 32,000,000bytes. Object arrays, nonfinite values, integer flux and extra keys are invalid. `np.savez` and `np.savez_compressed` are supported.

This example only packages already-computed fields; it supplies no method or answer:

```python
from pathlib import Path
import numpy as np

def save_result(case_id, psi_Wb):
    out = Path("/root/outputs/submission")
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "flux.npz", case_id=case_id, psi_Wb=psi_Wb)
```

Submit method code and assets that explain how the fields are produced from permitted physical inputs. `method.md` describes execution, software/data sources, stopping criteria, preservation of physical inputs, checks and limits for independent trace review. Numerical grading reads sealed `flux.npz`; it does not execute submission code or adjust scores for report quality.

Evaluation sequence and failures

1. Seal the submission after the solve ends and read its fields in an independent evaluator.
2. Validate NPZ structure, types,212 identities, shape and finiteness; align case IDs.
3. Apply the frozen dependencies and original diagnostic to all212 fields to obtain zeta.
4. Calculate E using the declared linear quantile, then Q using the fixed evaluator.
5. Retain E, E0, raw relative improvement `1-E/E0`, per-case zeta and valid-direction counts, and separately report the fraction below3.5cm.

Missing/corrupt data, wrong IDs/shapes/types, nonfinite fields, or failure to extract a finite boundary distance for any required case invalidates the data submission, Q=0. Do not drop failed cases. Valid worse-than-baseline results are scored by the fixed evaluator; negative raw improvement is retained.

Trusted-reference, dependency and evaluator faults are platform failures without a scientific score. Preserve sealed data for regrading after repair. Method provenance, physical-input compliance, credibility and scientific value are independently trace-reviewed and do not overwrite the numerical score.

Solve environment and resources

The solve limit is4hours with2CPUs and4096MiB RAM. Grading uses a separate environment. Official resources may be fetched and tools installed during solving; regenerating the baseline is not a prerequisite.

Scientific and public diagnostic dependencies are preinstalled in the isolated image environment `/opt/challenge-runtime/mastu` for Python3.12 on Linux; pinned versions are listed in `dependency-snapshot.json`. The default PATH selects this environment. It can also be invoked explicitly:

```bash
/opt/challenge-runtime/mastu/bin/python -c 'import numpy, scipy, freegs4e; print(numpy.__version__, scipy.__version__, freegs4e.__version__)'
```

This environment supplies scientific and diagnostic libraries, not every optional forward solver. See `resource.json` for solver access and usage. Runtime or external-acquisition faults are recorded separately from scientific difficulty.

Scope and references

Global optimality is not required. Numerical improvement establishes closer agreement with the EFIT++ reference boundaries on these212 fixed cases. Whether the method constitutes effective scientific optimisation is independently trace-reviewed against physical conditions and execution evidence. A high score alone does not establish experimental accuracy or improved control performance.

Full sources, versions, licences and access instructions are in `resource.json`.

Public resource location: environment/ contents are deployed directly to /root. Use /root if a tool shell does not inherit TF_PUBLIC_DIR. Use /opt/challenge-runtime/mastu/bin/python and add /root to the import path for public modules.

A development distance to the public archived FreeGSNKE baseline measures reproduction consistency, not the official E against EFIT++ reference. Baseline artifacts may support understanding/comparison; the submitted method must compute from declared physical inputs, not return a time-indexed archive lookup. EFIT++ evaluation outputs remain prohibited solver inputs. Preserve optional solver/replay and convergence evidence for independent trace assessment; reports/logs are not new numerical-scoring gates.
