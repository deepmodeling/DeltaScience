# O03：V外部患者验证

当前步骤提供另一组匿名患者表达数据及探针映射。当前数据语义见`/app/inputs/task_meta.json`。根据元数据恢复患者、疾病、组织和配对关系。

使用前序步骤形成的患者表达问题和程序定义开展验证。PN患者内病灶与非病灶配对为主要分析，其他疾病和健康材料为次级分析。分别报告程序整体、程序成员、逐患者方向以及对个别患者和个别成员的依赖。

完成综合报告，说明各阶段证据如何连接、哪些结果得到支持、哪些存在冲突或覆盖限制，并严格区分观察、关联、实验响应和因果结论。按照`/app/submission_schema.json`，将V阶段及最终综合判断的`results.jsonl`、`evidence_bundle.zip`、`final_report.md`和`code/`写入`/workspace/output/stages/v_validation/`；其中结构化记录均使用`stage=V`。另将整条链的最终综合报告写入`/workspace/output/final_report.md`。所有结构化结果使用统一schema，报告引用对应`record_id`。
