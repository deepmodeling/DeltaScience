# O03：B独立发现

当前步骤仅提供另一组匿名PN配对单细胞数据；A的原始数据和结果在本步骤均不可见。当前数据语义见`/app/inputs/task_meta.json`。独立完成B的QC、一级谱系、fibroblast二级状态、患者级组成与状态内表达；通路与CollecTRI覆盖总体fibroblast及满足覆盖要求的二级状态；LIANA按样本运行一级谱系和二级状态两种粒度。通路、TF和通讯均提交完整检验家族，并保留产生患者级支持检验的独立单位值。

本步骤只报告B自身结果、患者支持、稳健性和证据边界。跨队列比较将在下一步骤开放A、B结构化结果后完成。按照`/app/submission_schema.json`，将本阶段的`results.jsonl`、`evidence_bundle.zip`、`final_report.md`和`code/`写入`/workspace/output/stages/b_replication/`。
