Selective release in a frustrated amorphous trap network

Problem background

Design a reusable porous trapping material that releases a light mobile species A
while retaining a bound species B. Orientable trap complexes interact through
overlapping cooperative motifs and longer compatibility loops. Fully aligned
oriented motifs obstruct connected pores, raising the A-release barrier. Thermal,
flux, isotope, and cycling interventions expose different obstruction modes, but
all four act on the same material and processing schedule.

This is a self-contained synthetic effective model, not experimental data or an
atomistic simulator. All energies, rates, constitutive laws, and uncertainty
semantics are supplied. The challenge is frustrated discrete materials design,
not discovering a missing physical constant.

Approach

Choose 504 binary trap orientations and 72 real processing controls. Use the
transparent forward model or any equivalent implementation. Optimize nominal
selective release and, especially, the weakest local selective yield across all
four intervention families and both processing histories. Ordinary bulk-average
performance alone does not certify a usable network: each pore participates in
a series-connected collection path, so the least effective pore limits delivery.

The model has one gauge symmetry: changing every orientation's sign preserves
all physics. Arbitrary node permutations or partial sign changes are not gauge
symmetries. Node and zone indices are identities, not interchangeable labels.

Reproduction target

Return one feasible native material design. The target is high selective yield
throughout the declared uncertainty envelope, not just the provided calibration
draws. Selective yield is the released fraction of A multiplied by the retained
fraction of B. It lies in [0,1]. The joint physical metric is the minimum of this
yield over nodes, intervention scenarios, and forward/reverse histories.

The material has three chemical inventory classes. Each class contains 168 sites
and must contain exactly 84 positive orientations. The processing budgets are
24 × 750 K, 24 × 1 hour, and 24 × 15 K/s, respectively. Feasible per-zone ranges
are 650–850 K, 0.5–1.5 hours, and 5–25 K/s. Compatibility is quantified by the
seven-site loop blockade fraction and the root-mean-square processing residual;
minimize both. A nonzero frustrated-motif cost is a physical design deficiency,
not a malformed file. The forward model defines its consequences continuously.

Assets

Only this instruction and these registered resources are task-specific solver
inputs, available under `/workspace/resources/`:

- `network.json`: the nonperiodic interaction network, site properties, contacts,
  processing-zone coupling, and all coefficients with units.
- `model.md`: equations, schema, uncertainty envelope, and numerical conventions.
- `forward.py`: a NumPy-only O(n) forward evaluator for a fixed number of scenarios.
- `calibration.json`: 48 independent calibration scenarios, 12 per family.

Python 3.12, NumPy, and SciPy are available. No network query or external scientific
fact is needed. There are no allowed private resources. Computational budget:
3600 seconds on 4 CPU cores with 8 GiB RAM; use any optimization method within it.

Workflow steps

1. Load the registered coefficients and read the declared constitutive laws.
2. Search jointly over orientations and processing controls, preserving inventory
   and processing budgets; account for overlapping motifs and compatibility loops.
3. Evaluate all intervention families and both histories. Calibration draws are
   exchangeable examples, not an exhaustive specification of uncertainty.
4. Write one design as data only. The evaluator independently recomputes physics;
   do not submit a program, claimed observables, or a proof.

Output files

Write `/workspace/outputs/design.json`. This is the only required artifact.

Output contract

The JSON object has these four required arrays, in the supplied index order:

- `orientation`: exactly 504 integers, each either -1 or +1.
- `anneal_temperature_K`: exactly 24 finite real numbers, in kelvin.
- `dwell_hours`: exactly 24 finite real numbers, in hours, not seconds.
- `quench_K_per_s`: exactly 24 finite real numbers, in kelvin per second.

Arrays describe a single common design, not separate per-family designs. Do not
round the controls to integers; six decimal places are adequate. Processing
surrogates are calibrated only inside the declared ranges. Out-of-range controls
cannot support a physical release claim, although independent valid inventory
data remain interpretable. No exact decimal match to a reference is required.

Total output size must not exceed 2 MiB. Required data must be a regular file,
not a symbolic link. Extra fields or diagnostic files are neither required nor
trusted as observables; they do not substitute for the four arrays. Do not claim
scientific results without a minimally valid native design. A wholly missing or
malformed submission is an ordinary invalid submission, not evidence of cheating.

Self-check before finishing (optional, not scored)

No additional self-check output or execution log is required.

Platform scoring and execution limits

Submissions are evaluated by the private Harbor scientific checker and the platform's trajectory evaluator. The reported final score is the Harbor score multiplied by the trace factor. Submit the required output files and an authentic execution trajectory; preserve the file names, schemas and numerical requirements specified above. The platform may additionally review submissions.

The agent and verifier time limits and resource allocation are declared in `task.toml`. They are the configured limits, not a certified measurement of a from-scratch reference computation.

You have 3600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
