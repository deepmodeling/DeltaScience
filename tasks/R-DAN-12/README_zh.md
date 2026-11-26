# 31254.49.DELTASCIENCE.V1.R.DAN.12 — Danicopan 系列 `DAN-US2019-EX395`：开放路线逆合成与多路线排序

<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong> · <a href="../README_zh.md">← 返回全部开源题目</a>
</p>

| 字段 | 内容 |
| :--- | :--- |
| **中国科技资源标识（CSTR）** | [`31254.49.DELTASCIENCE.V1.R.DAN.12`](https://cstr.cn/31254.49.DELTASCIENCE.V1.R.DAN.12) |
| **官网题目页** | [https://deltascience.bohrium.com/questions/R-DAN-12](https://deltascience.bohrium.com/questions/R-DAN-12) |
| **学科大类** | 化学 |
| **细分类别** | 有机化学、药物化学 |
| **题型** | 工具调用与路线规划 |
| **评测时限** | 8 小时 |
| **贡献机构** | 深势科技、东京大学 |

---

## 科学目标

针对 Danicopan 系列目标分子 **`DAN-US2019-EX395`**，完成开放路线逆合成规划、工具验证与多路线排序，交付符合化学可行性与原料可得性要求的完整合成路线。

完整题面、工具接口与提交规范详见 [`instruction.md`](./instruction.md)。

## 独立评分与动态金标基线

- **动态金标对比**：[`tests/`](./tests/) 独立评分器首先对本题指定金标参考路线计算基线分 $G$，再逐条对正式提交路线评分得到 $S_i$；至少一条提交路线满足 $S_i \ge G$ 时记通过（`reward = 1`），全部低于 $G$ 或无可评提交记 `0`。
- **提交完整性**：未完成提交或被业务拒绝的候选路线不会被补造为正式答案；所有原始评判记录与证据回执均完整留痕。
- **参考解**：参考解位于 [`solution/`](./solution/)，评测时与 Agent 容器严格隔离。

## 合规与防污染声明

本题目、题面、参考解与评分脚本均受 DeltaScience 防污染条款约束，**严禁用于任何模型训练、微调、蒸馏或合成训练数据生成**。
