# Numeric scoring policy — gate-tolerance scientific version

Scientific version: qec-gate-tolerance-v2. Scoring version: noise-adapted-qec-tolerance-v5. The predecessor's two-budget fidelity score is a different scientific experiment; its old scores and blind rounds are retained, not silently reinterpreted.

## Scientific metric

One schema2 circuit pair, at most256 CX and256 rotations. Five stored wires and two clean recovery wires; all-to-all allowed gates. Complete encoding and recovery incur local Pauli errors: p per CX operand, (2/15)p per rotation. Seven specified thermal-rate stress cases, time4μs.

At p, the scientific margin is min_s[Favg_s(p)-B_s], using each same-condition bare-q0 result. Require margin>1e-10 from zero through the whole safe interval. No case label, condition-dependent circuit, postselection, subjective report or method-source requirement.

An analytic global Lipschitz bound is L=(2/3)*(2*N_CX+(2/15)*N_rot). Interval margin is at least min(endpoint margins)-L*width/2. Left-first subdivision certifies the entire prefix. An interior stopping bracket needs a genuinely failing upper endpoint under the stated 1e-10 comparison floor and width<=1e-7. Positive endpoints alone never justify accepting an unresolved interval. Minimum-width or evaluation-count exhaustion is a verifier failure, not numeric zero.

The measured value is the certified lower probability endpoint; retain the witness upper endpoint. Arithmetic uses floating-point density operators and explicit tolerance; this is not machine-verified outward-rounded interval arithmetic. p's public measurement domain ends at.01, independently of the reward mapping.

## Fixed published outcome and paper calibration

reference/reference.json freezes the author's t=4 VGQEC final encoding/adaptive recovery plus the complete standard recovery. Source commitf395f4893ca977c9751609ccf5191b7e8a8b5350, fig4b_data.py; no new training/search. Counts234CX+247rot fit the declared caps. Standard recovery channel equivalence was checked up to discarded-syndrome Kraus phases, with maximum matrix error3.84e-16.

Calibration tests invoke the actual runtime evaluator on all five frozen published outcomes under their original time/ideal-control conditions; Fe matches author source-figure coordinates within1e-7. The t=4 nominal result is Fe≈.98881603277, corresponding to Favg≈.99254402185. The extra stress cases and gate noise are benchmark extensions, not reproduced hardware experiments. Matching a preset0.2 score is not scientific calibration evidence.

## Mapping, independent of scientific computation

Let b>0 be the baseline's re-evaluated certified tolerance, x the candidate's. For x<=b, score=.2*max(0,x)/b. For x>b, score=.2+.8*clip((x-b)/(p_goal-b),0,1). Raw relative improvement is(x-b)/b and is retained separately. A valid identical baseline deterministically receives.2 by reusing exactly the same certificate. An empty circuit has no strict advantage and receives0.

The user confirmed p_goal=0.0001 (0.01%) on 2026-10-17; tests/scoring.json is the authoritative private policy. At the current certified baseline b=1.51824951171875e-5, this target is about 6.59 times the baseline tolerance. It asks for a substantial relaxation of gate precision requirements and is a challenge policy, not a paper optimum, physical upper bound or an attainability claim. No same-condition achievable construction or blind difficulty result is asserted. Numeric scoring never reads reports, source claims, research logs or training outputs. The solver-facing statements and interpretation contain the physical metric and submission contract, not the numerical score ceiling or mapping.

## Error and interface semantics

Successful grading prints one score and writes reward.txt. Invalid input yields numeric0 with normal exit. Trusted model/reference/policy, filesystem/dependency, nonfinite physical result or unresolved-certificate failure yields performance_score:null, nonzero exit and no valid reward.txt; stale reward files are removed first. Re-evaluate the same sealed submission after repair. result.json is grader-generated diagnostic output, never a second required submission artifact.

## Binary scoring overlay

The scientific model and continuous score above are unchanged. The final reward is 1 when the unrounded continuous performance score is at least 0.40, otherwise 0. `result.json` retains `continuous_score`, `performance_score`, the physical evidence and threshold. Invalid submissions remain zero; verifier failures have no valid reward and a nonzero exit. Historical scores remain unchanged.
