# 数据与计算来源

物理目标来自 Landreman–Paul 2022：[论文](https://doi.org/10.1103/PhysRevLett.128.035001)及[作者数据](https://zenodo.org/records/5645413)。

- environment/public/seed.json 来自作者 004 QA 冷启动目录的 input.nfp2_QA，仅包含圆截面的两个非零几何模式。
- solution/reference.json 来自 configurations/new_QA_well 中作者 010 精修构型，仅供组织者评估。
- 准对称评价使用 41 个磁面，s=0.25 的权重为 10；物理定义和数值设置见 instruction.md 及公开 case.json。
- environment/public/input.vmec 保留作者真空模型与原始磁通，边界由提交文件填入。

physics.py 是计算适配入口，调用 VMEC2000/STELLOPT、SIMSOPT、booz_xform、NEO 和 SIMPLE。NEO 对 iota_bar_fp 取绝对值以支持负旋转变换，SIMPLE 支持逐粒子退出码。上游版本、提交和构建方法见 runtime/Dockerfile；评分定义以本题程序和题面为准。
