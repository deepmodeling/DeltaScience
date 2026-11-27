# 31254.49.DELTASCIENCE.V1.QI.0002 — 噪声适配量子编码与恢复电路的门误差容忍度优化

<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong> · <a href="../README_zh.md">← 返回全部开源题目</a>
</p>

| 字段 | 内容 |
| :--- | :--- |
| **中国科技资源标识（CSTR）** | [`31254.49.DELTASCIENCE.V1.QI.0002`](https://cstr.cn/31254.49.DELTASCIENCE.V1.QI.0002) |
| **官网题目页** | [https://deltascience.bohrium.com/questions/QI-0002](https://deltascience.bohrium.com/questions/QI-0002) |
| **学科大类** | 物理学、数学与计算机 |
| **细分类别** | 量子计算、编码理论 |
| **题型** | 开放式设计与搜索 |
| **评测时限** | 12 小时 |
| **贡献机构** | 深势科技 |

---

## 科学目标

在门数受限（编码与恢复合计不超过 256 个 `CX` 门与 256 个旋转门，禁止测量、重置、经典反馈与后选择）且不按工况切换电路的约束下，设计一对确定性**编码与恢复电路**，使编码方案在全部 **7 种存储噪声工况**（$4\ \mu\text{s}$ 热弛豫/退相位）下持续优于同条件裸比特（$F_s(p) - B_s > 10^{-10}$），并最大化可认证的**门误差容忍度** $t$。

完整物理模型、七工况噪声表与输出格式详见 [`instruction.md`](./instruction.md)。

## 评分与独立认证

- **交付物**：`/app/outputs/submission.json`（`schema_version = 2`，含按执行顺序排列的 `encoder` 与 `decoder` 门列表）。
- **独立认证**：[`tests/`](./tests/) 评分器独立重算 Haar 平均逻辑保真度 $F_s(p) = (2F_e + 1)/3$，并采用解析 Lipschitz 界与自适应细分认证连续净保护前缀 $[0, t]$（区间宽度 $\le 10^{-7}$）。
- **计分口径**：以公开 VGQEC 参考方案容忍度 $b$ 为基准（0.20 分）、$T = 10^{-4}$ 为满分锚点（1.00 分），连续分 $S \ge 0.40$ 记通过。

## 运行环境与来源

- **环境**：Linux，4 CPU、8 GiB 内存、无 GPU；推荐与评分一致的 `/opt/quantum/legacy/bin/python`（Python 3.12、`NumPy 2.2.6`、`SciPy 1.15.3`）。
- **参考文献**：Shao et al., *Variational Graphical Quantum Error Correction Codes (VGQEC)*, `arXiv:2410.02608v2`。

## 合规与防污染声明

本题目、题面与评分脚本均受 DeltaScience 防污染条款约束，**严禁用于任何模型训练、微调、蒸馏或合成训练数据生成**。
