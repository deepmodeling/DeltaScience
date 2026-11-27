Retrosynthesis Route Design: 12_DAN_DAN_US2019_EX395

Run `retro context --variant "$RETRO_ACTIVE_VARIANT"` to inspect the active case. Use only this active variant.

Goal

Design and rank up to five distinct, complete routes for the exact target below.
Each terminal building block must pass the service's final stock check. Preserve
the defined target stereochemistry and explain the chemical basis of the ranking.
Collect five routes when the service permits. If it confirms executable search
is exhausted earlier, submit all collected routes with the allowed partial status.
Finding a preferred route alone does not establish search exhaustion.

Case Data

- Family: `Danicopan`
- Problem ID: `12_DAN_DAN_US2019_EX395`
- Route instance ID: `DAN-US2019-EX395`
- Target Full InChIKey: `CHGQWMNQJHOKGI-IDISGSTGSA-N`
- Target SMILES: `CC(=O)c1nn(CC(=O)N2C[C@@](F)(CN)C[C@H]2C(=O)Nc2cccc(Br)n2)c2ccc(-c3cnc(C)nc3)cc12`

Tools and Execution

Use the six native tools in
`/workspace/task/variants/open/data/tool_definitions.json`: `retro_get_state`,
`retro_predict`, `retro_expand`, `retro_check`, `retro_stock_check`, and
`retro_submit`. P-only means search and formal submission use this service's
observed graph state. SSR refers to its single-step retrosynthesis predictors.
Follow the schemas, enabled capabilities, observed graph versions and structured
Plan requirements. Use observed candidate IDs, assess chemistry, and revisit
alternative branches when a depth limit or stock miss prevents closure. A stock
hit establishes database availability, not reaction feasibility.

Deduplicate complete routes and rank them from best to worst. Submit every
collected route ID exactly once through `retro_submit`; the first is preferred.
Use `status=solved` with five collected routes, or `status=partial` when the
service confirms earlier exhaustion. With no complete route, follow the tool's
accepted partial/unsolved and budget-terminal conditions.

After submission, run `retro export --variant "$RETRO_ACTIVE_VARIANT"`.
The service generates `answer.json` and `scientific_trace.json`.
Keep `/workspace/outputs/variants/open/session.json` unchanged: evaluation reads
the submitted service record bound to this session. Handwritten or edited files
do not replace that formal submission. The answer contains `routes` and `ranking`,
including ordered forward steps, precursor/product SMILES, convergence and ranking
reasons. Runtime state, observations, receipts and validation belong in the trace.
Reference-library paths resolve against `/opt/retro/app`.

Evaluation

The seven chemical rubric dimensions and weights:

| Dimension | Points | Focus |
| --- | ---: | --- |
| Q-STEP | 28 | Reaction representation, atom origin and forward feasibility |
| Q-PRECEDENT | 10 | Structural precedent |
| Q-SEL | 14 | Target-specific selectivity |
| Q-STEREO | 14 | Defined stereochemistry and its supported transmission |
| Q-RPF | 14 | Target-specific key events and accepted structural equivalents |
| Q-CLOSE | 10 | Identity, graph, precursor completeness and verified stock closure |
| Q-MULTI | 10 | Quality-qualified independent routes and ranking |

The six-item score excludes Q-MULTI and has a maximum of 90. The designated gold
is a single literature route; its Q-MULTI is zero and it receives no supplementary
score bonus. Its leaves are checked by the same P-service under the frozen local
stock policy. Gold and submitted routes use the same chemical scoring framework.

Evaluation considers the first five routes in the submitted ranking, with no
backfilling from later routes. Q-MULTI counts only routes with Q-CLOSE=10, a
six-item score at least 90% of the current gold score, and a verified independent
key disconnection. The first qualifying route adds no points; each additional
one adds 2.5, up to 10. Key-disconnection groups are defined by mapped bond cuts
in the final target-forming transformation; changing only route IDs or leaving
groups does not establish independence. Missing decisive mapping evidence remains
unresolved. The existing Q-RPF bound-based ranking penalty can halve Q-MULTI.

The task passes when the best of these five routes has its six-item score plus
quality-filtered Q-MULTI greater than or equal to the gold score from the same
evaluation. Equality passes. No additional rounding is used for comparisons.
The full original collection and ranking remain available for auditing.

Within an evaluation, normalized identical routes share LLM-judged subitems;
program values remain specific to each route's own evidence. If the best route's
total is within 10 points of gold, both routes' LLM subitems receive two additional
judgments, each subitem takes the median of three, and the original aggregator
recomputes the result. A new best route in this band is reviewed at most once;
no normalized route receives more than three scientific judgments per subitem.
The fixed judge is `deepseek-v4.1-flash-1017`. Trace quality is reported separately.
Missing critical evidence or infrastructure errors do not become a normal zero.
A target-specific checkpoint that is demonstrably absent from the submitted
route receives zero from the program; mapping failures and unresolved
structural-equivalence evidence remain pending.

Limits and Integrity

- Wall time: 28800 seconds.
- Maximum retrosynthesis depth: 20.
- Maximum collected/ranked routes: 5.
- Graph nodes, LLM calls, tool calls, provider requests and turns remain subject
  to the limits in the active task and the service's enforcement.

Work as the configured unprivileged user (UID 1000). Change search state only
through native tools. Do not alter task data, service processes or receipts,
invoke the verifier, or write reward files. Respect the time limit; reaching it
alone is not proof of executable-search exhaustion.
