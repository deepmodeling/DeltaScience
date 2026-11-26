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
| **贡献机构** | 北京科学智能研究院、浙江大学 |

---

## Harbor 题包与公开镜像说明

本目录包含完整的 9 阶段 Harbor 题包（`task.toml`、`environment/Dockerfile`、各阶段 `steps/` 题面与隔离环境脚本，以及 `steps/v_validation/tests/` 中的完整 `o03_scorer_v2` 自动评分器）。多队列单细胞转录组与组织蛋白质组数据矩阵已预置在公开科研运行镜像（`registry.dp.tech/public/pkscience-o03-agent` 与 `registry.dp.tech/public/pkscience-o03-verifier`）中。

---

## 科学目标

结节性痒疹（Prurigo Nodularis，PN）是一种以慢性瘙痒和结节性皮肤纤维化为特征的炎症性皮肤疾病。单一单细胞队列中的差异并不必然代表稳健的疾病机制，可能受患者个体差异、细胞组成比例变化、组织采样或技术批次效应混杂。

本题要求 AI Agent 完整执行 **9 阶段端到端多组学疾病机制研究与证据整合**：

1. **阶段 A — 独立发现**：基于 PN 配对病灶/非病灶皮肤单细胞数据（`GSE233280`），完成质控、谱系注释、成纤维细胞二级状态识别、患者级组成与状态内表达比较、通路与 CollecTRI 转录因子分析及 LIANA 细胞通讯推断。
2. **阶段 B — 独立队列发现**：在严格不访问 A 队列原始数据与结果的隔离条件下，对独立配对 PN 队列（`GSE273559`）独立完成全流程分析。
3. **阶段 AB — 跨队列重复性检验**：仅依据 A、B 阶段结构化结果（通过 `record_id` 引用），系统区分跨队列共同支持、队列特异、方向不一致及覆盖不足的发现。
4. **阶段 C — 疾病背景及组织区室分析**：在 PN、特应性皮炎（AD）与健康对照单细胞队列（`GSE222840`）中，聚焦成纤维细胞、血管内皮细胞与血管壁相关细胞三类区室评估疾病特异性。
5. **阶段 R — 上游候选响应分析**：基于参考响应矩阵系统筛选进入实验检验的上游调控候选与疾病程序。
6. **阶段 D（盲态）— 实验响应分析**：在未知处理名称与遗传背景含义的盲态条件下，分析人皮肤成纤维细胞扰动响应矩阵（`GSE137108`）。
7. **阶段 D（解码）— 实验条件解释**：结合解码映射表与冻结的盲态结果及 A–C 患者证据，区分共同响应、背景依赖响应与未获实验支持的机制假设。
8. **阶段 E — 患者组织蛋白质组验证**：独立开展组织蛋白质组差异与功能分析（`PXD072618` / `IPX0014987001`），明确区分跨组学一致、冲突与蛋白检测覆盖受限的信号。
9. **阶段 V — 外部患者验证及综合解释**：在独立外部配对队列（`GSE261704`）上验证疾病程序并形成最终综合证据链，严格区分 `observation`、`association`、`experimental_response` 与 `causal` 证据层级。

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

本题目规范、数据与评分规则均受 DeltaScience 防污染条款约束，**严禁用于任何模型训练、微调、蒸馏或合成训练数据生成**。
