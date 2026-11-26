# O03：A–C候选响应分析

当前步骤提供固定响应参考矩阵以及A–C的已提交结果。当前资源语义见`/app/inputs/task_meta.json`。根据A–C形成的患者级端点，在各材料中对完整可观察候选集合进行统一分析。

报告每个候选的覆盖、方向、跨材料一致性、排名稳健性和对端点定义的依赖，并据此选择进入实验数据检验的候选及疾病程序。候选选择需引用A–C和本步骤的结构化结果。按照`/app/submission_schema.json`，将本阶段的`results.jsonl`、`evidence_bundle.zip`、`final_report.md`和`code/`写入`/workspace/output/stages/r_response/`。
