# R-DAN-12 可执行参考解

活动参考：`solution/checkpoint_aligned_reference.json`。回放计划包含10个共价步骤、5种叶节点身份。

默认solve入口依次通过普通原生工具初始化、查询状态、预测、精确匹配前体身份、应用已观察候选、检查原料和化学、提交及导出。参考路线完成后继续遵循原生五条路线或真实搜索耗尽的结束条件，参考路线优先排名。找不到候选或工具拒绝会明确失败，不伪造提交、原料证据或奖励。

本题引用的公共合成支路已随私有solution补齐，共1个依赖文件；不再依赖原材料中的宿主机绝对路径。

非活动collection金标已按2026-11-12材料恢复，其SHA-256与原冻结来源完全一致。实际评分仍使用既有checkpoint_aligned_reference及私有gold_reference，七步主体结构原本已与修复材料一致，本次未修改活动评分结构、依赖、检查点或阈值。详见authoring/reference-source-alignment.json。

使用随包Harbor启动入口保留原评分服务。真实SSR/stock闭合、GPU/Judge及金标动态分数比较尚未验证；--export-only只导出计划材料，不表示Oracle成功。

## 当前评分规则（1.0.17）

同轮先评指定金标的六项化学分G，金标MULTI为0且不额外加分。只评提交排名前5条，以其中最高六项分加质量过滤后的MULTI与G比较，相等通过；第6条及以后不补位。质量MULTI、原排名减半、近10分逐子项三次中位数及缺失事件程序锁分，以当前instruction.md和tests/reward-policy.json为准。

历史参考分数不作为当前阈值；缺失关键证据、未决或基础设施异常不补造正常reward。Trace质量独立报告。--export-only只验证并导出计划，不代表已完成原生回放或Oracle。
