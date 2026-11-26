# 31254.49.DELTASCIENCE.V1.T14 — 陷阱取向与工艺控制联合优化的稳健选择性释放

<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong> · <a href="../README_zh.md">← 返回全部开源题目</a>
</p>

| 字段 | 内容 |
| :--- | :--- |
| **中国科技资源标识（CSTR）** | [`31254.49.DELTASCIENCE.V1.T14`](https://cstr.cn/31254.49.DELTASCIENCE.V1.T14) |
| **官网题目页** | [https://deltascience.bohrium.com/questions/T14](https://deltascience.bohrium.com/questions/T14) |
| **学科大类** | 材料科学、数学与计算机 |
| **细分类别** | 材料设计、运筹学 |
| **题型** | 开放式设计与搜索 |
| **评测时限** | 1 小时 |
| **贡献机构** | 深势科技 |

---

## 科学目标

在包含 **504 个二元陷阱节点**（分 3 类化学节点，每类 168 个且正取向须严格为 84 个）与 **24 个工艺分区**（退火温度、停留时间、淬火速率共 72 个连续变量，受区间与总预算约束）的受挫非晶陷阱网络中，联合优化离散取向与连续工艺控制，使**选择性产率**（A 释放比例 × B 保留比例）在热、通量、同位素、循环四类干预及正反两种历史下的**最弱孔道联合指标**达到高稳健水平。

完整题面与正向物理模型定义详见 [`instruction.md`](./instruction.md)，公开网络输入已预置在公开科研镜像（`registry.dp.tech/public/pkscience-t14-agent`）中。

## 独立验证与运行环境

- **交付物**：`/workspace/outputs/design.json`（含 `orientation[504]` 及三组长度 24 的工艺参数数组）。
- **独立重放评分**：[`tests/checker.py`](./tests/checker.py) 基于隐藏的 `tests/reference_resources/` 独立重放物理模型，从取向/工艺合法性、库存/预算、七节点环相容性、名义产率与联合稳健性能（占 64/100 分）进行严格验收。
- **环境**：Linux，4 CPU、8 GiB 内存、无 GPU；Python 3.12、`NumPy`、`SciPy`（见 `environment/Dockerfile`）。

## 合规与防污染声明

本题目、题面、参考文件与评分脚本均受 DeltaScience 防污染条款约束，**严禁用于任何模型训练、微调、蒸馏或合成训练数据生成**。
