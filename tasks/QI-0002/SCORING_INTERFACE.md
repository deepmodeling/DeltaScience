# 数值评分接口

```bash
bash tests/test.sh /path/to/outputs /path/to/result
```

也支持SUBMISSION_DIR、RESULT_DIR和原有默认路径，命令行参数优先。输入目录只需一个符合公开schema2的submission.json。平台无需读取报告、训练记录或自报指标，不执行提交代码。

评价成功时退出0，RESULT_DIR/reward.txt只含一个[0,1]数值，是调用方唯一必须读取的输出。stdout也只打印这一分数。非法提交按公开规则给0，正常完成评价。

可信资源、依赖、I/O或数值认证出现故障时退出非零，result.json中的performance_score为null，不生成有效reward.txt；重用目录时清理之前的reward.txt，避免把历史分数当作本次结果。此类故障不是科学表现差。

result.json由评价端自行生成，保留候选与公开参照的门误差容忍区间、原始相对改善、资源数、工况向量、比较容差和评分版本。它是诊断输出，不是额外提交要求。只有固定公开电路、可信物理配置和提交电路参与数值评价。公开物理模型与评分端受信副本逐字一致；原论文成果校准及独立信道检查另有证据，不以两份相同代码相互印证代替科学校准。

Submission handoff: the solver writes `/app/outputs/submission.json`; the default verifier submission root is `/app/outputs`. A caller restoring sealed artifacts elsewhere must pass that absolute root as the first argument (or SUBMISSION_DIR); an explicit argument takes precedence. Verify the sealed manifest/hash and transfer receipt before grading. A missing file caused by handoff failure must be diagnosed at the platform boundary; a genuinely missing solver submission remains invalid.

## 二值评分

按原模型计算的连续分大于等于 0.40 时 reward.txt 为 1，否则为 0；未四舍五入后比较。result.json 保留 continuous_score、performance_score 和原物理指标。非法提交按原协议记 0；评分故障非零退出，不产生有效 reward。
