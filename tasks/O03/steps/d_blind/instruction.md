# O03：D编码条件下的实验响应

当前步骤提供人皮肤成纤维细胞的log2表达矩阵和编码样本信息。当前数据语义见`/app/inputs/task_meta.json`。根据样本表恢复细胞线、背景代码、处理代码、时间和可估计的实验比较。

使用前序步骤选择的候选和疾病程序，分析各编码条件相对基线的时间响应、细胞线一致性、程序内部结构和异质性。当前步骤只解释编码条件下的响应，不包含生物学条件名称。按照`/app/submission_schema.json`，将本阶段的`results.jsonl`、`evidence_bundle.zip`、`final_report.md`和`code/`写入`/workspace/output/stages/d_blind/`。
