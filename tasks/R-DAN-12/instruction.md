Design and rank up to five distinct, complete open-route retrosynthetic pathways for the target molecule below using the native retrosynthesis service. Every terminal building block must pass the service's stock check, and defined target stereochemistry must be preserved.

Target case:
- Family: `Danicopan`
- Instance ID: `DAN-US2019-EX395`
- Full InChIKey: `CHGQWMNQJHOKGI-IDISGSTGSA-N`
- SMILES: `CC(=O)c1nn(CC(=O)N2C[C@@](F)(CN)C[C@H]2C(=O)Nc2cccc(Br)n2)c2ccc(-c3cnc(C)nc3)cc12`

Tools and workflow:
1. Run `retro context --variant "$RETRO_ACTIVE_VARIANT"` to inspect the active case.
2. Use the six native tools defined in `/workspace/task/variants/open/data/tool_definitions.json`: `retro_get_state`, `retro_predict`, `retro_expand`, `retro_check`, `retro_stock_check`, and `retro_submit`.
3. Collect up to five distinct complete routes (maximum depth 20), deduplicate them, rank them from best to worst with chemical justifications, and submit every collected route ID exactly once via `retro_submit` (`status=solved` for five routes, or `status=partial` only when the service confirms executable search exhaustion).
4. After submission, run `retro export --variant "$RETRO_ACTIVE_VARIANT"` to generate `answer.json` and `scientific_trace.json`. Leave `/workspace/outputs/variants/open/session.json` unmodified; formal evaluation reads the service-bound session record.

Evaluation rubric:
Routes are evaluated on seven chemical dimensions: Q-STEP (28), Q-PRECEDENT (10), Q-SEL (14), Q-STEREO (14), Q-RPF (14), Q-CLOSE (10), and Q-MULTI (10, rewarding independent key disconnections among the top five ranked routes). The best submitted route is compared against the literature reference route evaluated under the same scoring framework and stock policy.

Work as UID 1000 and modify search state only through the native tools. Time limit: 8 hours.
