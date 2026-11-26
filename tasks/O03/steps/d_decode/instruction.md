# O03：D条件解码与实验解释

当前步骤新增D条件代码与生物学处理、遗传背景的映射，文件位置见`/app/inputs/task_meta.json`。将映射应用于D盲态分析，评价不同处理与背景如何改变前序候选和疾病程序，并区分共同响应、背景依赖和未得到实验支持的解释。

提交解码后的实验判断及其与A–C患者结果的关系，引用D盲态结果记录。按照`/app/submission_schema.json`，将本阶段的`results.jsonl`、`evidence_bundle.zip`、`final_report.md`和`code/`写入`/workspace/output/stages/d_decode/`。
