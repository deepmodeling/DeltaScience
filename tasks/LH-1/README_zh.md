# 31254.49.DELTASCIENCE.V1.LH.1 — 仿星器准轴对称边界优化（`PRECISE_QA`）

<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong> · <a href="../README_zh.md">← 返回全部开源题目</a>
</p>

| 字段 | 内容 |
| :--- | :--- |
| **中国科技资源标识（CSTR）** | [`31254.49.DELTASCIENCE.V1.LH.1`](https://cstr.cn/31254.49.DELTASCIENCE.V1.LH.1) |
| **官网题目页** | [https://deltascience.bohrium.com/questions/LH-1](https://deltascience.bohrium.com/questions/LH-1) |
| **学科大类** | 物理学 |
| **细分类别** | 聚变与等离子体 |
| **题型** | 开放式设计与搜索 |
| **评测时限** | 24 小时 |
| **贡献机构** | 深势科技 |

---

## 科学目标

从简单的 $n_{\text{fp}} = 2$ 圆环初始边界出发，优化三维等离子体边界的 Fourier 展开系数（交付 `/app/boundary.json`），在满足准轴对称性、磁阱、旋转变换、有效纹波与高能粒子约束等全部物理门槛的前提下，将仿星器展弦比压低至 $A \le 6$，构建更紧凑的高约束准轴对称磁笼。

完整题意、归一化约定（有效小半径 $1.70\text{ m}$、轴上 Boozer 场强 $B_{00} = 5.70\text{ T}$）与评分细则见 [`instruction.md`](./instruction.md)。

## 镜像构建与本地运行

`environment/Dockerfile`（Agent 镜像）与 `tests/Dockerfile`（独立评分镜像）共享完全一致的底层科研运行时（基于 `python:3.12-slim-bookworm` 与 `tests/build-inputs/` 随包源码，含 `STELLOPT` / `VMEC2000` / `NEO`、`SIMPLE`、`libneo`、`simsopt`、`jax`/`jaxlib`、`booz_xform` 等，构建前逐项校验 SHA-256）。参考物理背景：Landreman & Paul, *Phys. Rev. Lett.* 128, 035001, 2022。

```bash
bash build.sh                               # 构建 Agent 与独立 Verifier 镜像（共享缓存）
bash run.sh                                 # 交互求解，工作目录挂到 /work
bash evaluate.sh work/boundary.json         # 用独立评分镜像评估候选边界
bash run-reference.sh                       # 复算参考解
```

- **资源配置**：Linux/amd64（`jaxlib` 需 AVX），24 CPU、64 GiB 内存、20 GiB 磁盘；解题时限 24 小时，评分时限 12 小时，运行期断网隔离。
- **验收标准**：展弦比 $A \le 6$ 且全部物理约束门槛同时满足得 `1`，否则得 `0`；参考解位于 `solution/`（不进入 Agent 镜像）。

## 合规与防污染声明

本题目、题面、参考解与评分脚本均受 DeltaScience 防污染条款约束，**严禁用于任何模型训练、微调、蒸馏或合成训练数据生成**。
