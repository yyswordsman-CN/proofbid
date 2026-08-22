# PREEXISTING_IP — ProofBid

> 建立日期：2026-08-19。该清单用于区分既有经验、比赛期新增工作和禁止进入公开提交的资产。

## 当前结论

- 本项目目录在 2026-08-19 创建，此前只有 AGENTS.md 项目合同。
- 本轮实现为独立新写，不复制其他本机项目的源代码、Prompt、Schema、模板、测试夹具、品牌、配置或数据。
- 当前仅只读参考用户已授权盘点的工程经验和本项目 AGENTS.md 中的抽象原则。

## 只允许借鉴思想的既有项目

| 来源 | 允许范围 | 禁止范围 |
|---|---|---|
| 工程招投标项目 | 需求抽取、证据映射、BOM、偏离和终审的业务思想 | 源码、模板、客户数据、品牌、配置 |
| 可审计经营分析闭环智能体 | 状态、回执、Gate、Trace、Replay 的工程思想 | 源码、Schema、生产数据、部署配置 |
| TCL Auto Order | 分层、幂等、写前确认和 unknown 阻断思想 | 生产代码、群聊、订单、接口、凭据 |
| 华南地级市分析报告 | 数据审计、叙事和实体产物 QA 思想 | 业务明细、报告模板、城市数据 |
| Orbit Desktop | Provider Adapter、凭据隔离和证据等级思想 | 源码、签名配置、Provider 凭据 |

## 2026-08-19 起的比赛期新增工作

- ProofBid Python 本地纵向切片；
- 合成招标文件、投标主体资料和产品目录；
- EvidenceRef、Requirement、MatchRecord、ArtifactReceipt 等本项目合同；
- 规则型要求抽取和合成产品匹配基线；
- Excel、Word、JSON、ZIP Renderer 与 Validator；
- Trace、CLI、测试和 Demo 产物；Replay 仍未实现。
- ProofBid `TaskSpec`、`ExecutionPlan`、`ProviderReceipt`、计划策略、Google Adapter 边界和 agentic pipeline；这些代码为本项目独立新写。
- 2026-08-22 新增完全合成的绿色与缺授权案例、`ReadinessDecision`、受控 ADK `FunctionTool` 运行时、工具回执、有限 Renderer 恢复、FastAPI/React Workbench、Cloud Run Service/Job 与 Cloud Storage 适配和部署资产；均为本项目独立新写。

## 本轮新增外部依赖

| 依赖 | 版本 | 来源与许可证 | 用途 |
|---|---:|---|---|
| Google Agent Development Kit for Python | 2.7.1 | Google 官方 PyPI/GitHub，Apache License 2.0 | `Agent`、`App`、`Runner`、会话和结构化 Planner |
| Google Gen AI Python SDK | 2.18.1 | Google 官方 PyPI/GitHub，Apache License 2.0 | Gemini 类型、Thinking/Retry 配置和事件元数据 |
| Pydantic | 2.13.4（当前解析版本） | PyPI，MIT License | ADK Planner 输出 Schema 的运行时校验 |
| FastAPI / Uvicorn | 见 `pyproject.toml` | MIT / BSD-3-Clause | 同源任务 API 与 ASGI 服务 |
| Google Auth / Cloud Storage | 见 `pyproject.toml` | Apache-2.0 | ADC、Cloud Run v2 调用与任务对象存储 |
| React / Vite / Playwright | 见 `apps/web/package-lock.json` | MIT / Apache-2.0 | 英文 Workbench、构建与响应式验收 |

以上只引入公开依赖和 API，不复制 Google 样例源码、Prompt、数据或品牌资产。项目已采用 Apache-2.0；版本与许可证边界以 `pyproject.toml`、`apps/web/package-lock.json` 和 `THIRD_PARTY_NOTICES.md` 为准，最终容器仍需保存解析后的依赖与镜像 digest。

## 后续要求

- 每次引入外部依赖、数据、图片、模型、Prompt 或代码片段时，记录来源、版本、许可证和用途。
- Rules 快照不替代参赛人对完整资格、IP 与跨赛复用条款的最终确认。
- 公共仓库和提交包不得包含用户真实业务数据、客户信息、价格、凭据、内部路径或其他项目资产。
