> **PK Science continuous scoring (v1)**
> The final Harbor reward preserves the original continuous score, instead of applying the legacy 0/1 pass threshold. The original score is retained in `result.json` at `continuous_score` (scale 0–1); reward = original score / 1. This replaces statements about the final binary reward below. Scientific calculations, submission requirements, integrity checks and original per-item scoring stay in force. Legacy pass/fail gates remain diagnostic. An incomplete evaluator result is not a measured zero. See `pkscience_scoring.json`.

# 受限电路下噪声适配量子编码的门误差容忍度

## 研究背景

量子纠错把一个未知量子态分散到多个物理比特上，希望在存储后恢复逻辑信息。但增加冗余也增加了编码和恢复操作：理想噪声模型中的保护优势，可能被执行这些操作时的门误差抵消。对小型量子设备而言，重要的问题不仅是某个编码在理想条件下有多好，还包括它要求量子门精确到什么程度，才值得使用。

不同物理比特的噪声也并不均匀。VGQEC 的公开研究采用一组 IBM-LIMA 的历史相干时间，展示了噪声适配的五比特码相对于标准五比特码的优势。论文在这个数值实验中把编码与恢复视为理想操作；公开最终参数可以直接用于成果评价，不需要重新训练。其恢复过程包含额外辅助位及标准码恢复，完整实现的成本都应计入。VarQEC 的纠错条件优化和 Channel-Optimized Quantum Error Correction 的联合编码恢复优化，为寻找合适结构提供了方法背景，但相应代价函数不直接等于含门误差的净保护收益。

本题研究一套固定电路在有限资源和噪声失配下的门精度要求。提高门误差容忍度，意味着同样的存储保护不再依赖那么精确的门操作；同时要求各个公开工况都获得净收益，可以防止只改善某个噪声点、却让其他条件下的量子信息保护变差。结论限于本题模型与有限压力测试，不代表连续噪声空间、具体硬件或所有纠错方案的全局性能界。

## 任务

提交一对确定性编码和恢复电路，提高它在全部公开工况中仍优于同条件裸比特时的门误差容忍度。同一对电路用于所有工况和所有门误差水平，不能读取工况标签或按评价参数切换电路。目标是保护任意未知逻辑量子态，以 Haar 平均逻辑保真度评价。

公开参照为 `/app/reference.json` 中的固定 VGQEC 最终方案及其完整恢复电路。来源、原条件校准指标和编译说明见 `/app/BASELINES.md`。评价端直接重算参照和提交，不执行训练，不采用文件中的自报性能。只需提交电路结果，不要求附交研究报告。

## 物理模型与资源

q0 是逻辑输入和输出，q1…q4 初始为 |0000>。编码只使用 q0…q4；随后这五位经历一次 4 μs 存储。恢复开始时才加入处于 |00> 的 q5、q6，恢复可使用全部七位。最后保留 q0，迹掉其他六位。初始态和辅助位制备理想；不存在测量、重置、经典反馈或后选择。矩阵约定中 q0 为最低有效位。

允许全连接的 RX、RY、RZ 和有方向的 CX。编码与恢复合计最多 **256 CX、256 个旋转门**。旋转按 exp(-iθP/2) 定义，θ 用弧度，必须有限且 |θ|≤100π。每个列出的门均执行并计入资源与门误差，包括零角旋转；若无需某门，应从提交中删除。没有额外的深度限制。

每个 CX 后，对其两个操作比特分别施加独立局部 Pauli 信道：

\[
\mathcal D_p(\rho)=(1-p)\rho+\frac p3(X\rho X+Y\rho Y+Z\rho Z).
\]

每个旋转后，在其操作比特施加同型信道，错误概率为 2p/15。p 是单个操作比特的总 Pauli 错误概率，不是整个 CX 的平均门不保真度。评价范围为 0≤p≤0.01；门时长造成的额外闲置退相干不在本模型内。完整恢复中所有门都按相同规则计入，不存在免费的理想标准恢复。

存储噪声在五位上独立作用：第 i 位的激发态占据衰减为 exp(-t/T1_i)，相干项衰减为 exp(-t/T2_i)，t=4 μs。名义参数来自论文的历史快照：

| 参数 / μs | q0 | q1 | q2 | q3 | q4 |
|---|---:|---:|---:|---:|---:|
| T1 | 97.51 | 127.61 | 92.68 | 79.36 | 19.76 |
| T2 | 178.3 | 109.28 | 120.95 | 35.71 | 19.4 |

设弛豫速率 r1_i=1/T1_i，纯退相位速率 rφ_i=1/T2_i-r1_i/2。下表的倍数分别乘在这两组速率上，随后由 T1'_i=1/r1'_i、T2'_i=1/(r1'_i/2+rφ'_i) 得到各工况。这样保持热噪声信道的物理有效性。±25% 是本题明确设定的压力测试，不是论文测得的漂移范围。

| 工况 | 弛豫速率倍数 q0…q4 | 纯退相位速率倍数 q0…q4 |
|---|---|---|
| nominal | 1,1,1,1,1 | 1,1,1,1,1 |
| relaxation_bias | 1.25,1.25,1.25,1.25,1.25 | 0.75,0.75,0.75,0.75,0.75 |
| dephasing_bias | 0.75,0.75,0.75,0.75,0.75 | 1.25,1.25,1.25,1.25,1.25 |
| q0_relaxation | 1.25,1,1,1,1 | 1,1,1,1,1 |
| q0_dephasing | 1,1,1,1,1 | 1.25,1,1,1,1 |
| spatial_shift_A | 1.25,1,1,1,0.75 | 0.75,1,1,1,1.25 |
| spatial_shift_B | 0.75,1,1,1,1.25 | 1.25,1,1,1,0.75 |

所有具体参数和资源约束固定在 `/app/config.json`。裸比特对照是 q0 不执行任何门、在同一存储工况下直接输出，不随 p 增加人为控制误差。

## 指标与评价

工况 s、门误差 p 下的平均保真度记为 F_s(p)，裸比特为 B_s。通过逻辑 Bell 态得到纠缠保真度 Fe 后，使用 F_s=(2Fe+1)/3。它不是最坏输入态保真度。净保护要求每个工况均有 F_s(p)-B_s>10^-10。

门误差容忍度是从 p=0 开始，所有较低门误差都保持上述净保护的连续区间上端；若 p=0 已无净收益，容忍度记为零。评价不假定保真度对 p 单调：使用解析 Lipschitz 界、自适应区间细分与 10^-10 保真度比较容差，给出保守下端点和首个失效点的上端点，p 的区间宽度不超过 10^-7。完全通过评价域时记录该域端点。数值结果与浮点容差有关，不是形式化区间算术证明；具体算法公开在 `/app/tolerance.py`。

数值评分只随经验证的门误差容忍度改善而提高。非法电路或无法获得净收益的结果不获得优化收益；评价实现、依赖或数值认证故障与科学得分分开处理，不会把平台故障记成性能差。

设候选电路的经认证容忍度为 `t`，固定公开参照电路在相同条件下重新计算的容忍度为 `b`，满分目标 `T = 0.0001`。连续分为：当 `t ≤ b` 时，`S = 0.2 × max(0, t) / b`；当 `t > b` 时，`S = 0.2 + 0.8 × min(1, (t − b) / (T − b))`。因此基准得 0.2 分，`t ≥ T` 得 1 分，未四舍五入的 `S ≥ 0.40` 对应 `t ≥ b + 0.25 × (T − b)`。满分目标是评分锚点，不代表已证明存在可达到它的方案。


## 提交格式

只提交 `/app/outputs/submission.json`，UTF-8 JSON，不超过 2,000,000 字节，禁止 NaN、Infinity 和符号链接。格式如下；示例仅说明字段，**不是优化解**：

```json
{
  "schema_version": 2,
  "encoder": [
    {"gate": "RY", "qubits": [0], "theta": 0.25},
    {"gate": "CX", "qubits": [0, 4]}
  ],
  "decoder": [
    {"gate": "CX", "qubits": [5, 0]},
    {"gate": "RZ", "qubits": [0], "theta": -0.25}
  ]
}
```

每个列表按执行顺序排列。CX 的 qubits 为 [控制位,目标位]，不带 theta；旋转恰有一个操作比特且必须带 theta。门对象只允许示例对应字段，比特编号必须是整数且不能重复，encoder 不得使用 q5、q6。encoder 与 decoder 可为空列表。schema_version 必须是整数 2；根对象的其他字段不参与数值评价。

可运行 `/opt/quantum/legacy/bin/python /app/baseline.py --output /app/outputs/submission.json` 导出公开参照，或使用公开物理模型研究其他方案。`/app/schema.md` 说明接口，`/app/resources.yaml` 列出材料；不需要网络或账号。评价方运行固定入口后读取一个数值分，无需解题者提供额外输出或人工裁决。

## 作答资源与时限

作答环境为Linux，配备4 CPU、8 GiB内存，无GPU；作答时限为12小时。提交后的独立评分不计入作答时限。


运行命令与数值数组转换示例见 `/app/RUNTIME.md`；请使用其中明确给出的解释器绝对路径。


## Binary evaluation / 二值评分

Binary evaluation converts the original continuous score to 1 if it is at least 0.40, or 0 otherwise; comparison uses the unrounded value. Grader diagnostics retain the continuous score. Verifier failures produce no valid score.

二值评分按原模型计算连续分，未四舍五入的分数大于等于 0.40 记 1，否则记 0；原连续分保留在诊断中，评分故障不产生有效得分。
