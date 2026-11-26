# BCL2 与 BCLXL 对照分子的身份与来源

三种分子用于作者侧身份和文献方向核对。它们不是新设计候选清单，也不是预计算的当前题目答案。

## 实验方向

| 分子 | BCL2 Ki nM | BCLXL Ki nM | 原始实验与用途 |
| --- | --- | --- | --- |
| Venetoclax / ABT-199 | <0.0100 | 48 | Souers 2013 Supplementary Table 2，同表 TR-FRET；C03 正向、C04 反向 |
| Navitoclax / ABT-263 | 0.044 | 0.055 | 同一补表、同类 TR-FRET；两题双靶计算 baseline |
| A-1331852 / compound 13 | 6.1 | <0.01 | Wang 2020 Table 5，同表 BCL2/BCLXL TR-FRET；C04 正向、C03 反向 |

保留 < 符号。不得把检测边界当作精确等值，不把同文的细胞 EC50 与结合 Ki 混合，也不将来自两篇文章的结果冒充同一批实验数据。A-1331852 的 6.3 nM 是 MOLT-4 细胞 EC50，不是其 BCLXL Ki。

- Souers 原始研究：[10.1038/nm.3048](https://www.nature.com/articles/nm.3048)。公开[补充材料](https://media.springernature.com/original/springer-static/esm/art:10.1038%2Fnm.3048/MediaObjects/41591_2013_BFnm3048_MOESM22_ESM.pdf)第 8 页 Supplementary Table 2 给出 navitoclax 与 ABT-199 的配对 TR-FRET Ki。
- Wang 原始研究：[10.1021/acsmedchemlett.9b00568](https://pmc.ncbi.nlm.nih.gov/articles/PMC7549103/)，Figure 1 将 A-1331852 对应为 compound 13，Table 5 给出上述配对 TR-FRET Ki。

## Venetoclax

- 官方结构：[PDB 6O0K](https://www.rcsb.org/structure/6O0K)，其 CCD 配体为 [LBM](https://www.rcsb.org/ligand/LBM)。LBM 页面明确列有 Venetoclax 同义名。
- 分子式：C45H50ClN7O7S；CCD 分子量 868.439。
- InChIKey：`LQBVNQSMGBZMKD-UHFFFAOYSA-N`。
- 机器可读 SMILES 采用 CCD LBM 的 OpenEye canonical 版本，见 environment/inputs/literature_controls.json。
- 结构原始论文：[Birkinshaw 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6547681/)。该文明确说明 4MAN 是 venetoclax 类似物，不能标成 venetoclax 本体；6O0K 才是本文 WT 结合结构。受体构建体、截短和晶体工程改造仍须按 PDB 实际记录披露，不能仅凭 WT 名称假定全长天然构建体。

## Navitoclax

- 官方结构：[PDB 4LVT](https://www.rcsb.org/structure/4LVT)，CCD 为 [1XJ](https://www.rcsb.org/ligand/1XJ)。
- 分子式：C47H55ClF3N5O6S3；CCD 分子量 974.613。
- InChIKey：`JLYAXFNOILIKPP-KXQOOQHDSA-N`。
- CCD 含一个指定的 R 手性中心。必须使用含 `N[C@H]` 的 canonical isomeric 字符串，不能拿不含手性的一般 SMILES 替代。
- 4LVT 是 BCL2 上的 navitoclax，不能据此声称已获取 navitoclax 在 BCLXL 上的同一晶体姿势。另一受体来源需独立核验并冻结。

## A-1331852

- 原始发现文献 Figure 1 / compound 13 是身份与实验方向的一手依据。
- 本包不提供 A-1331852 本体的实验共晶姿势。尤其 [6VWC/RQ7](https://www.rcsb.org/ligand/RQ7) 是吡啶甲基类似物，分子式 C32H25N7O3S、CCD 分子量 587.651；其图结构并非含 adamantane 的 A-1331852。
- 机器可读 SMILES 可从美国 NCI 的[官方 CellMinerCDB A-1331852 登记](https://discover.nci.nih.gov/drugs/cellminercdb/A-1331852_cellminercdb.html)获得，NSC 797172、PubChem CID 71565985，分子式 C38H38N6O3S。这是官方登记，非供应商转述，其来源类型是官方结构登记，而非作者 SI molfile。
- [IUPHAR/BPS 官方结构条目](https://www.guidetopharmacology.org/GRAC/LigandDisplayForward?ligandId=11102&tab=structure)独立列出同结构的 SMILES、InChI 和 InChIKey `QCQQONWEDCOTBV-UHFFFAOYSA-N`。其页面的“molecular weight 658.27”接近该式的单同位素质量口径，不能直接当 RDKit MolWt；实际评分一律由冻结 RDKit 从 SMILES 重算。
- environment/inputs/literature_controls.json 同时保存 NCI SMILES 和 IUPHAR 标识；清理后分子式和 full InChIKey 已核对。来源类型为官方结构登记，不标为原文机器可读结构抽取。

## 不能直接继承的 C02 条件

Venetoclax 和 navitoclax 均显著超过 550 Da；A-1331852 同样超过 550 Da。三者结构和性质不能套用 olaparib 的 QED 改善与 ESOL 绝对硬门。BCL 家族采用主合同规定的宽性质包络，QED、ESOL、SA 和三个警示目录都只报告。

本文件只陈述文献事实、身份及合同边界，不包含任何本题 docking 结果、候选优化或验证尝试。
