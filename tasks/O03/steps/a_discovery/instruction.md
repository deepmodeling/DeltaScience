# O03：A独立发现

当前步骤提供A的匿名原始单细胞counts和样本信息。患者内病灶与非病灶配对，患者是疾病比较的独立单位。当前数据语义见`/app/inputs/task_meta.json`。

按照`/app/analysis_config.json`完成单细胞QC、图构建、一级谱系注释和fibroblast二级状态分析。随后完成患者级组成和状态内表达；通路与CollecTRI覆盖总体fibroblast及满足覆盖要求的二级状态；LIANA按样本运行一级谱系和二级状态两种粒度。通路、TF和通讯均提交完整检验家族，并保留产生患者级支持检验的独立单位值。

从A中报告跨患者重复的主要变化、其患者支持、稳健性、替代解释和证据边界，并提出可由独立患者材料检验的问题。按照`/app/submission_schema.json`，将本阶段的`results.jsonl`、`evidence_bundle.zip`、`final_report.md`和`code/`写入`/workspace/output/stages/a_discovery/`。
