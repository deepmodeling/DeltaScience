# 31254.49.DELTASCIENCE.V1.FUS.0001 — 托卡马克自由边界平衡求解优化（MAST-U 放电 45425）

<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong> · <a href="../README_zh.md">← 返回全部开源题目</a>
</p>

| 字段 | 内容 |
| :--- | :--- |
| **中国科技资源标识（CSTR）** | [`31254.49.DELTASCIENCE.V1.FUS.0001`](https://cstr.cn/31254.49.DELTASCIENCE.V1.FUS.0001) |
| **官网题目页** | [https://deltascience.bohrium.com/questions/FUS-0001](https://deltascience.bohrium.com/questions/FUS-0001) |
| **学科大类** | 物理学 |
| **细分类别** | 聚变与等离子体 |
| **题型** | 数值仿真与计算 |
| **评测时限** | 4 小时 |
| **贡献机构** | 深势科技 |

---

## 科学目标

在英国 MAST-U 托卡马克常规偏滤器放电 **45425** 的全部 **212 个固定时刻**下，严格保持机器几何、主动线圈与被动结构电流、等离子体电流 $I_p$ 与 Lao 剖面参数不变，改进静态轴对称**自由边界 Grad–Shafranov 平衡数值求解方法**，缩小计算所得等离子体核心边界与 EFIT++ 参考分支之间的几何差异。

完整物理约束与数据格式详见 [`instruction.md`](./instruction.md)。

## 交付物与科学验收规则

- **交付物**：`/root/outputs/submission/` 下的 `flux.npz`（含 212 个唯一 `case_id` 与形状 `(212, 65, 65)` 的总极向磁通场 `psi_Wb`，单位 Wb，$R \in [0.06, 2.0]\text{ m}, Z \in [-2.2, 2.2]\text{ m}$）、可复跑代码 `solve.py`/`solve.sh` 及方法说明 `method.md`。
- **误差指标**：独立评分器（`tests/metric_core.py`）使用冻结的 Separatrix 诊断在 360 个极向角上计算每时刻核心边界最大偏差 $\zeta$，并取线性 95% 分位值 $E = 0.55 z_{200} + 0.45 z_{201}$。
- **计分口径**：官方 FreeGSNKE 基线 $E_0 = 35.109\text{ mm}$ 得 `0.20` 分，$E \le 30\text{ mm}$ 得满分 `1.00`，$E \ge 50\text{ mm}$ 得 `0` 分；连续分 $Q \ge 0.40$（即 $E \le 33.83\text{ mm}$）记通过。

## 运行环境与来源

- **环境**：Linux，2 CPU、4096 MiB 内存；固定科学环境 `/opt/challenge-runtime/mastu`（Python 3.12、`NumPy`、`SciPy`、`freegs4e`、`Shapely`、`Numba`、`h5py`）。
- **论文与数据来源**：Pentland 等，*Physica Scripta* 100 (2025) 025608（`DOI: 10.1088/1402-4896/ada192`）；官方数据 `DOI: 10.14468/26m5-ey02`。

## 合规与防污染声明

本题目、题面与评分脚本均受 DeltaScience 防污染条款约束，**严禁用于任何模型训练、微调、蒸馏或合成训练数据生成**。
