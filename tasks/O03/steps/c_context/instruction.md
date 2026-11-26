# O03：C疾病背景与组织区室分析

当前步骤提供PN与炎症性皮肤病对照的匿名单细胞数据，以及A、B步骤结果。当前数据语义见`/app/inputs/task_meta.json`。独立完成C的QC和一级谱系注释，并对fibroblast、endothelial和mural进行二级状态分析；mural由pericyte与smooth_muscle细胞共同构成。

在患者层面完成组成和状态内表达；通路与CollecTRI覆盖三个总体区室及满足覆盖要求的二级状态；LIANA按样本运行一级谱系和二级状态两种粒度。通路、TF和通讯均提交完整检验家族，并保留产生患者级支持检验的独立单位值。利用C判断A/B共同发现的疾病背景、区室位置和替代解释，同时报告C中新出现的结果。按照`/app/submission_schema.json`，将本阶段的`results.jsonl`、`evidence_bundle.zip`、`final_report.md`和`code/`写入`/workspace/output/stages/c_context/`。
