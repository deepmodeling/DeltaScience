Read /workspace/task/task.json and each enabled variant's instruction.md,
data/task.toml, data/target.json, data/reference_inputs.json and
data/tool_definitions.json below /workspace/task/variants/<variant>/.
The scientific configuration is restored to data/task.toml inside the container.

Use the six native P tools through the live service:
retro init --variant <variant>
retro call --variant <variant> --tool <native tool> --arguments @/workspace/arguments.json
retro export --variant <variant>

Call retro_submit before exporting. Hand-written results do not submit routes.
The CLI creates /workspace/outputs/variants/<variant>/session.json containing the
service-issued session_id, coordinator_id and variant. Keep that file unchanged;
the verifier uses it to export the canonical answer, trace and validation receipt
from the same live service. Routes and ranking follow the published native schema;
answer.json has exactly the top-level keys routes and ranking.

The trusted root ENTRYPOINT starts the service; solve as retro (UID1000).
Keep the same container and service alive through automatic verification.
Service or scoring infrastructure errors are recorded without normal reward.
Do not invoke the verifier or write reward files. The original coordinator code is retained at retro coordinator / solution/solve.sh,
but this candidate has not validated its protected-reference import boundary.
Use the native CLI directly until that optional adapter is verified.

Resolve relative reference-library paths in reference_inputs.json against
/opt/retro/app. Reference hashes use UTF-8 text with leading/trailing whitespace
stripped, exactly as the original context metadata functions specify.

Solve the single open run within its original 8-hour limit. The main reward is
the original answer quality score divided by 100. Trace quality is independent.
