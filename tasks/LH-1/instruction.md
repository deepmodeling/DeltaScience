> **PK Science continuous scoring (v1)**
> The final Harbor reward preserves the original continuous score, instead of applying the legacy 0/1 pass threshold. The original score is retained in `result.json` at `continuous_score` (scale 0–1); reward = original score / 1. This replaces statements about the final binary reward below. Scientific calculations, submission requirements, integrity checks and original per-item scoring stay in force. Legacy pass/fail gates remain diagnostic. An incomplete evaluator result is not a measured zero. See `pkscience_scoring.json`.

# 守住粒子，把准轴对称磁笼做得更紧凑

三维磁笼能不能做得更小，同时让粒子感受到近似轴对称的场强规律？请从一个简单圆环出发，调整等离子体外边界，在保持准轴对称性、磁阱和粒子约束的条件下，尽量减小展弦比 A。

**只提交一份 `boundary.json`。** 物理指标由公开评估器重新计算。

## 1. 为什么值得做

展弦比 A 可以理解为环的大半径与小半径之比。本题把小半径统一到 1.70 m，因此 A 更小，就意味着大环绕得更紧。

难点在于，缩小这个环可能同时改变磁场强度的规律、磁力线的绕转和粒子轨道。准轴对称性有助于减少粒子的向外漂移，但形状改得更紧凑时，仍要用输运指标和粒子轨道计算检查是否保住了性能。你的目标是在这些要求下，找到更紧凑的边界。

## 2. 给定条件与性能要求

起点 `/app/seed.json` 是圆截面圆环，环境同时提供 VMEC 模板 `/app/input.vmec`、物理程序和公开评估器。它提供初始几何，可以先调整三维模式、求得平衡，再对候选做完整评估。

| 固定条件 | 取值 |
|---|---|
| 场周期数 | nfp=2，采用仿星器对称边界 |
| 平衡模型 | 固定边界，零压强，处处为零的包围净环向电流 |
| 尺寸与粒子计算场强 | 小半径 1.70 m，轴上 Boozer B₀₀ 为 5.70 T |
| 可调整的量 | 描述边界形状的 Fourier 系数，可以增加模式 |

**通过标准：展弦比 A≤6，且以下性能要求全部满足。** 全部达标得 1，否则得 0。

| 保持的性能 | 本题要求 | 物理含义 |
|---|---|---|
| 41 面准轴对称误差 Q | ≤ 3.2×10⁻⁶ | 从内部到边缘保持很小的对称误差 |
| 平均旋转变换 | 接近 0.42，相对偏差 ≤ 1% | 保持磁力线的绕转程度 |
| 端点真空磁阱 | ≥ 0.0048 | 保留有利的体积导数变化 |
| 四面有效纹波最大值 | ≤ 0.0022% | 控制一类低碰撞率输运 |
| α 粒子损失与未解析数之和 | 4096 条轨道中最多 1 条 | 在 0.2 s 追踪内尽量保住高能粒子 |

## 3. 用 JSON 描述最终设计

最终只提交 `/app/boundary.json`，用 UTF-8 JSON 描述边界。例如：

```json
{"nfp": 2, "modes": [
  {"m": 0, "n": 0, "rbc": 1.0, "zbs": 0.0},
  {"m": 1, "n": 0, "rbc": 0.2, "zbs": 0.2}
]}
```

这个例子用于说明格式；完整起点在 `seed.json`。每个模式给出整数 m、n 和有限实数 rbc、zbs，表示

```text
R(θ,φ) = Σ rbc(m,n) cos(mθ − n·nfp·φ)
Z(θ,φ) = Σ zbs(m,n) sin(mθ − n·nfp·φ)
```

m≥0；m=0 时使用 n≥0。未列出的模式为零，模式顺序不限，`zbs(0,0)=0`。所有长度系数使用同一单位，整体尺度由评估器统一到小半径 1.70 m。每个 `(m,n)` 只列一次，`rbc(0,0)>0`。

可以增加模式、自选优化方法。无需提交优化历史、搜索脚本或自报物理量。

## 4. 评测与评分

最终奖励已改为二值化：**展弦比 A≤6，且第 2 节列出的所有性能要求同时达标，reward=1；任一项未达标，reward=0。** 不要求把展弦比进一步降低到基准的 90%。

判定逐项使用 `/app/case.json` 中原有的基准门槛：

- 上限项：指标值≤原 `reference`。
- 下限项：指标值≥原 `reference`。
- 匹配项：`abs(指标值−reference)≤width`，旋转变换的原目标与 1% 容差不变。
- α 粒子项：确认损失数与未解析数之和≤1（4096 条轨道）。

各阈值及等号均按原题意保留；浮点边界比较仅允许 1e-12 相对舍入误差，不是物理阈值的额外放宽。`result.json` 中的 `continuous_score`、各分项 `score` 和 `completion` 仅供诊断，正式 `reward` 与 `reward.txt` 只输出 0 或 1。`all_constraints_satisfied` 给出总判定，各分项 `passed` 给出逐项判定。

提交缺失、格式错误或候选的物理计算失败时记 0 分，并说明原因；环境错误另行报告，不伪造 reward。

## 5. 第一次动手

环境提供 `/app/physics.py`、`/app/evaluate.py` 和数值配置 `/app/case.json`。可以先复制起点，随后改写其中的几何：

```bash
cp /app/seed.json /app/boundary.json
python /app/evaluate.py --submission /app/boundary.json --output /work/evaluation
```

`/work/evaluation/result.json` 给出主目标、各项是否达标及最终二值奖励；连续评分仅作诊断。每次评估使用新的输出目录。正式评分从最终几何重新计算，使用相同的程序和参数。

本题离线作答。可以使用环境内的物理程序、优化库、本地文档和通用示例，自行组织优化；禁止联网获取现成解、已优化的边界或线圈，以及本题的完整优化或复现脚本。

资源为 24 核 CPU、64 GiB 内存，无 GPU；解题预算 24 小时，单次评分最多 12 小时。

直接求解平衡时，调用环境中的 `xvmec2000`，再用 `simsopt.mhd.Vmec(wout文件路径)` 读取结果。搜索阶段可以自行安排成本更低的计算。

## 6. 怎样评价你的磁笼

收到边界后，评估器先把有效小半径统一到 1.70 m，再用 [VMEC](https://github.com/PrincetonUniversity/STELLOPT) 求解真空磁场。展弦比 A 取 VMEC 的 `aspect`，平均旋转变换取均匀磁通半网格上的平均值，也就是 `Vmec.mean_iota()`。这样，不同设计就在相同尺寸下比较形状和磁力线的绕转。

接着，从磁轴到边缘逐层看场强是否保持准轴对称。这里用 s 表示归一化环向磁通：磁轴是 0，边界是 1。Q 采用 [SIMSOPT](https://github.com/hiddenSymmetries/simsopt) 的 `QuasisymmetryRatioResidual`，对称方向为 `(helicity_m,helicity_n)=(1,0)`；在 s=0、0.025、…、1 的 41 个磁面上计算平方残差并加权求和，其中 s=0.25 的权重是 10，其余为 1。这个数反映从内部到边缘的对称误差，越小越好。

磁阱则看磁通面之间的体积如何变化。设 V′=dV/ds，本题用 `W=(V′(0)−V′(1))/V′(0)` 比较核心与边缘，调用 `Vmec.vacuum_well()` 计算。正值表示体积导数从核心到边缘有所下降。随后，磁场经 [booz_xform](https://github.com/hiddenSymmetries/booz_xform) 转换到 Boozer 坐标，由 NEO 在最接近 s=0.2、0.4、0.6、0.8 的四个磁面上计算有效纹波，取最大值参与评分。它衡量低碰撞率下的一类输运，报告值为 `ε_eff=EPSTOT^(2/3)`。

最后看高能粒子能不能留下来。磁场的轴上 Boozer 零模 B₀₀ 统一到 5.70 T 后，[SIMPLE](https://github.com/itpplasma/SIMPLE) 从 s=0.25 的薄壳释放 4096 个 3.5 MeV α 粒子，位置按体积采样，速度方向各向同性，追踪无碰撞导心轨道至 0.2 s。越过 s=1 的轨道计为损失；未能完成数值追踪的轨道也计入本题的未约束数。这一项评价的是这批固定测试粒子的约束表现。

网格、固定采样与求解精度可在 `/app/case.json`、`/app/input.vmec` 和 `/app/physics.py` 中查看。提交更高阶的 Fourier 模式时，评估器会相应加密计算。

## 7. 背后的研究

这道题参考了 [Landreman 和 Paul 关于高精度准对称磁场的研究](https://doi.org/10.1103/PhysRevLett.128.035001)。他们通过调整三维边界，把准对称性、磁阱和粒子约束结合起来。这里沿用这些物理目标，请你从简单圆环出发，在保住性能的同时，把磁笼做得更紧凑。
