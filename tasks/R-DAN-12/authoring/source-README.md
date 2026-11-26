# Harbor 格式候选

本目录是一个完整 Harbor 任务根，包含固定科学代码、四SSR权重、ZINC库存、
公开题面、原内置Agent及私有评分资源。task.toml为唯一Harbor配置。

状态：UNVALIDATED_CANDIDATE。本次未构建Docker、未运行GPU解题或在线裁判。
保留原依赖快照与角色安装配方；依赖可安装性及原服务器等效性待验证。
评分所需RETRO_JUDGE_API_KEY/RETRO_JUDGE_URL/RETRO_JUDGE_MODEL由可信运行端配置；
可选coordinator使用独立RETRO_SOLVER_*配置。凭据不随题包提供。

根instruction.md说明公开输入、原科学时限、提交方式和实际reward映射。
查看authoring/conversion.json和provenance/dependencies了解范围及来源。
