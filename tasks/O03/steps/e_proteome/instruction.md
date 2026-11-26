# O03：E患者组织蛋白质组

当前步骤提供PN、疾病对照和健康对照的匿名患者组织蛋白质组。当前数据语义见`/app/inputs/task_meta.json`。根据样本元数据恢复分组、采集顺序、蛋白覆盖和缺失模式。

先独立完成蛋白差异和功能分析，再将前序实验与患者端点映射到蛋白层。PN与疾病对照为主要比较，健康对照用于次级比较。报告方向一致、方向不同、覆盖不足和可能受技术结构影响的结果，并形成可由外部患者表达材料检验的问题。按照`/app/submission_schema.json`，将本阶段的`results.jsonl`、`evidence_bundle.zip`、`final_report.md`和`code/`写入`/workspace/output/stages/e_proteome/`。
