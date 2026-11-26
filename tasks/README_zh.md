# DeltaScience v1.0 开源代表题目目录

<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong> · <a href="../README_zh.md">← 返回 DeltaScience 主页</a>
</p>

为防止数据污染、维护评测公信力，**DeltaScience v1.0** 的全部 **65 道非公开任务**在活跃期内保持非公开。同时，为便于科研与产业社区了解标准 Harbor 题包结构、独立评分器设计与科学验收口径，我们开源 **7 道覆盖各核心学科领域的高质量代表题目**。

DeltaScience 为所有入选题目提供**中国科技资源标识（CSTR）**——由中国科学院计算机网络信息中心建设运营，根据国家标准《科技资源标识》建立的科技资源统一标识体系，为各类科技资源提供全球唯一、长期有效的标识，实现科技资源全球范围快速定位与获取。

## 题目总览

| 中国科技资源标识（CSTR） | 学科大类 | 题目主题 | 题型 | 时限 | 说明文档 |
| :--- | :--- | :--- | :--- | :---: | :---: |
| [`31254.49.DELTASCIENCE.V1.C.03`](https://cstr.cn/31254.49.DELTASCIENCE.V1.C.03) | 化学、生命科学 | BCL2 / BCL-XL 选择性分子设计 | 开放式设计与搜索 | 5h | [英文](./C-03/README.md) · [中文](./C-03/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.R.DAN.12`](https://cstr.cn/31254.49.DELTASCIENCE.V1.R.DAN.12) | 化学 | Danicopan 系列 `DAN-US2019-EX395`：开放路线逆合成与多路线排序 | 工具调用与路线规划 | 8h | [英文](./R-DAN-12/README.md) · [中文](./R-DAN-12/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.O03`](https://cstr.cn/31254.49.DELTASCIENCE.V1.O03) | 生命科学 | 结节性痒疹成纤维细胞病理状态的跨队列发现与多组学验证 | 多阶段数据分析与论证 | 8h | [英文](./O03/README.md) · [中文](./O03/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.QI.0002`](https://cstr.cn/31254.49.DELTASCIENCE.V1.QI.0002) | 物理学、数学与计算机 | 噪声适配量子编码与恢复电路的门误差容忍度优化 | 开放式设计与搜索 | 12h | [英文](./QI-0002/README.md) · [中文](./QI-0002/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.FUS.0001`](https://cstr.cn/31254.49.DELTASCIENCE.V1.FUS.0001) | 物理学 | 托卡马克自由边界平衡求解优化（MAST-U 放电 45425） | 数值仿真与计算 | 4h | [英文](./FUS-0001/README.md) · [中文](./FUS-0001/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.T14`](https://cstr.cn/31254.49.DELTASCIENCE.V1.T14) | 材料科学、数学与计算机 | 陷阱取向与工艺控制联合优化的稳健选择性释放 | 开放式设计与搜索 | 1h | [英文](./T14/README.md) · [中文](./T14/README_zh.md) |
| [`31254.49.DELTASCIENCE.V1.LH.1`](https://cstr.cn/31254.49.DELTASCIENCE.V1.LH.1) | 物理学 | 仿星器准轴对称边界优化（`PRECISE_QA`） | 开放式设计与搜索 | 24h | [英文](./LH-1/README.md) · [中文](./LH-1/README_zh.md) |

## 标准 Harbor 题包结构

```text
<TASK_ID>/
├── README.md             # 英文题目总览、元数据、CSTR 与验收说明
├── README_zh.md          # 中文题目总览
├── instruction.md        # 完整题面、科学约束与交付物规范
├── task.toml             # 算力资源（CPU/内存/GPU）、时限与元数据配置
├── environment/          # Dockerfile 及锁定版本的科研依赖与公开输入
├── tests/                # 独立评分器脚本与定量科学验收规则
└── solution/             # （如适用）参考验证脚本
```

## 合规与防污染声明

> **重要提示**：任何机构或个人**不得将 DeltaScience 评测集题目（含本仓库开源代表题目、题面、参考方案与评分脚本）及其改写、翻译、变体用于训练、微调、蒸馏任何模型，或用于生成合成训练数据**；不得批量爬取、商业销售或用于营利活动。
