# 31254.49.DELTASCIENCE.V1.O03 — 结节性痒疹成纤维细胞病理状态的跨队列发现与多组学验证

<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong> · <a href="../README_zh.md">← 返回全部开源题目</a>
</p>

| 字段 | 内容 |
| :--- | :--- |
| **中国科技资源标识（CSTR）** | [`31254.49.DELTASCIENCE.V1.O03`](https://cstr.cn/31254.49.DELTASCIENCE.V1.O03) |
| **官网题目页** | [https://deltascience.bohrium.com/questions/O03](https://deltascience.bohrium.com/questions/O03) |
| **学科大类** | 生命科学 |
| **细分类别** | 生物组学、免疫与炎症 |
| **题型** | 多阶段数据分析与论证 |
| **评测时限** | 8 小时 |
| **算力配置** | 4 CPU · 16 GB 内存 |
| **贡献机构** | 北京科学智能研究院、浙江大学 |

---

## Harbor 题包与数据说明

本目录包含标准化的 Harbor `v1.1.0` 题包（[`instruction.md`](./instruction.md)、[`task.toml`](./task.toml)、基于公开镜像 `python:3.13.5-slim` 的 `environment/Dockerfile`、`environment/resources/` 公共通路/转录因子/配受体参考库、`tests/` 独立评分器套件 `o03_scorer_v2` 与 `o03_atomwise`，以及 `solution/` 参考验证入口）。

由于 `environment/inputs/` 下的原始单细胞矩阵总计约 **1.46 GB**（部分 `.mtx.gz` 单文件超过 GitHub 100 MB 硬限制），该目录以 [`environment/inputs/README.md`](./environment/inputs/README.md) 保留完整文件清单与全部公开 GEO / ProteomeXchange 数据来源。

---

## 科学目标

结节性痒疹（Prurigo Nodularis，PN）是一种以慢性瘙痒和结节性皮肤纤维化为特征的炎症性皮肤疾病。本题要求 AI Agent 在 `/workspace/output` 下完整执行 **9 阶段患者级跨队列多组学机制研究与证据整合**（详见 [`instruction.md`](./instruction.md)）：

1. **阶段 `A`（`stages/a_discovery`）**：在 PN 配对病灶/非病灶皮肤单细胞队列（`GSE233280`）上独立完成质控、谱系与成纤维细胞亚群注释、患者级组成/表达比较、通路、CollecTRI 转录因子与 LIANA 细胞通讯分析。
2. **阶段 `B`（`stages/b_replication`）**：在独立配对 PN 单细胞队列（`GSE273559`）上独立重复分析。
3. **阶段 `AB`（`stages/b_compare`）**：跨队列重复性检验，区分共同支持、队列特异、方向冲突与覆盖不足的发现。
4. **阶段 `C`（`stages/c_context`）**：在 PN、特应性皮炎（AD）与健康对照队列（`GSE222840`）中围绕成纤维细胞、内皮细胞与血管壁相关细胞评估疾病特异性。
5. **阶段 `R`（`stages/r_response`）**：基于固定响应参考矩阵（`environment/resources/stage_response_reference.tsv`）对上游调控候选进行排序筛选。
6. **阶段 `D_BLIND`（`stages/d_blind`）**：在盲态条件下分析人皮肤成纤维细胞扰动实验数据（`GSE137108`）。
7. **阶段 `D_DECODE`（`stages/d_decode`）**：结合 `D_key/condition_key.csv` 解码实验条件并与患者级证据整合。
8. **阶段 `E`（`stages/e_proteome`）**：独立开展患者皮肤组织蛋白质组验证（`PXD072618` / `IPX0014987001`），兼顾缺失模式与采集顺序结构。
9. **阶段 `V`（`stages/v_validation`）**：在独立外部配对队列（`GSE261704`）上验证疾病程序并形成综合证据链，严格区分 `observation`、`association`、`experimental_response` 与 `causal` 证据层级。

---

## 独立评分规则

独立评分容器（`tests/Dockerfile`，基于 `python:3.13.5-slim`）在不执行提交代码的前提下汇总全部 9 个阶段目录，校验 Schema 规范与全局唯一 `record_id` 证据引用，并通过 **43 个评分 atom** 分别评估过程证据、生物学结果与结构化综合结论。完整 100 分制连续科学分保留于 `score.json` 与 `run_report.json`，二值验收门槛为 **$\ge 70 / 100$**。

---

## 公开数据来源

- **GSE233280** — PN 配对病灶/非病灶皮肤单细胞转录组（PMID: 38246584）· [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE233280)
- **GSE273559** — 独立 PN 配对单细胞队列（PMID: 37506977）· [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE273559)
- **GSE222840** — PN、AD 与健康皮肤单细胞转录组（PMID: 37210042）· [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE222840)
- **GSE137108** — 人皮肤成纤维细胞炎症 / TGF-β 刺激响应数据 · [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE137108)
- **PXD072618 / IPX0014987001** — PN、AD 与健康对照皮肤组织蛋白质组 · [ProteomeXchange](https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD072618)
- **GSE261704** — 独立 PN 配对外部表达验证队列（PMID: 41333131）· [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE261704)

---

## 合规与防污染声明

本题目、题面、参考文件与评分脚本均受 DeltaScience 防污染条款约束，**严禁用于任何模型训练、微调、蒸馏或合成训练数据生成**。
