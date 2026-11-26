> 历史记录：本文件记录二值评分改造前的连续分复现结果，并非当前 `reward.txt` 的二值奖励。当前评价以题面及评分器约定为准。

# Baseline复现与独立评分

公开baseline是可复现的比较起点，不是最优解或满分参考解。导出入口只读取公开冻结成果，不训练、不搜索，也不读取评分端私有材料。

## 导出baseline

在题目固定镜像中，公开environment文件按原运行布局部署后执行：

```sh
python /app/export_baseline.py --output-dir /app/outputs
```

正式交接只封存outputs的实际结果文件。可选研究对照算法的复现与这个冻结成果导出是不同工作，不将后者冒称前者。

## 独立评分

在同一精确digest的新评分环境中，只部署题包tests与封存输出；不复用Agent的工作目录、Python缓存、安装结果或日志。按平台既有映射运行：

```sh
sh /tests/test.sh /submission /logs/verifier
```

环境、资源和超时以task.toml为准，未因本轮自检改变。评分进程非零退出、reward缺失或诊断为基础设施异常时均属未评分；不能替换为科学零分。非法/空提交仍按原契约计分。

## 本轮证据（2026-10-21）

本轮已全量复算：reward约0.2；空提交0。

使用精确digest镜像文件系统和清理后的工作目录验证；不冒称Docker/Harbor或完整cgroup验收。

详细回执、原始baseline产物、错误分类和资源范围见仓库trace/engineering/20261021-baseline-independent。没有新增模型盲解，也没有修改历史成绩。
