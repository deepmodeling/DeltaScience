# 31254.49.DELTASCIENCE.V1.C.03 — BCL2 / BCL-XL 选择性分子设计

<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong> · <a href="../README_zh.md">← 返回全部开源题目</a>
</p>

| 字段 | 内容 |
| :--- | :--- |
| **中国科技资源标识（CSTR）** | [`31254.49.DELTASCIENCE.V1.C.03`](https://cstr.cn/31254.49.DELTASCIENCE.V1.C.03) |
| **官网题目页** | [https://deltascience.bohrium.com/questions/C-03](https://deltascience.bohrium.com/questions/C-03) |
| **学科大类** | 化学、生命科学 |
| **细分类别** | 药物化学、化学信息学、结构生物学 |
| **题型** | 开放式设计与搜索 |
| **评测时限** | 5 小时 |
| **贡献机构** | 深势科技、北京科学智能研究院 |

---

## 科学目标

围绕 **BCL2**（`6O0K` A 链）与 **BCL-XL**（`4QVX` A 链）同源靶点，设计一组骨架多样、优先保留 BCL2 结合活性并削弱 BCL-XL 脱靶结合的小分子候选组合，同时满足类药性、理化性质与结构合理性等综合约束。

完整题面、计算评分定义与必交文件规范详见 [`instruction.md`](./instruction.md)，公开结构输入已预置在公开科研镜像（`registry.dp.tech/public/pkscience-c-03-agent`）中。

## 独立评分与参考解说明

- **独立评分**：[`tests/`](./tests/) 中的独立评分器仅读取声明的分子交付产物，并重新计算全部对接、选择性与组合多样性指标；公开自检报告仅作求解过程反馈，不直接采信为最终得分。
- **参考解状态**：当前题包未附带 `solution/` 可执行参考解或占位解答，求解系统需基于公开结构输入与自检工具自主完成搜索优化。
- **资产完整性**：[`ASSET_HASHES.json`](./ASSET_HASHES.json) 记录了 `environment/`、`tests/` 与 `authoring/` 的校验哈希。

## 运行环境

- 不可变 Linux/amd64 科学镜像，预装 Python 3.11、AutoDock Vina 1.2.7、tmux 3.5a 及锁版本 Python 科学依赖（见 `environment/Dockerfile` 与 `environment/runtime-base.Dockerfile`）。

## 合规与防污染声明

本题目、题面、输入与评分脚本均受 DeltaScience 防污染条款约束，**严禁用于任何模型训练、微调、蒸馏或合成训练数据生成**。
