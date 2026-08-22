# Google All Things Agentic — Rules Snapshot

> 快照日期：2026-08-22。用途：ProofBid 开发与提交门禁。官方 Rules、FAQ 和后续公告始终优先于本文件。

## 官方入口与时间

- 赛事主页：https://allthingsagentichackathon.devpost.com/
- Rules：https://allthingsagentichackathon.devpost.com/rules
- Resources：https://allthingsagentichackathon.devpost.com/resources
- FAQ：https://allthingsagentichackathon.devpost.com/details/faqs
- 官方开发节奏：https://allthingsagentichackathon.devpost.com/updates/45652-how-to-plan-your-project
- 正式截止：2026-08-31 17:00 PDT，即北京时间 2026-09-01 08:00。
- 官方建议：8 月 24 日前完成开发，25–26 日录制视频，28 日提前提交。
- Google Cloud Credits 申请截止：2026-08-28 12:00 PT 或额度用完即止。

## ProofBid 的参赛定位

- 主类别：The Taskmaster。
- 附加奖项目标：Individual / Hobbyist 与 Best Architectural Design；Startup Excellence 是附加资格，不是主类别替代项。
- Taskmaster 要求事件触发的多步后台任务、Agent 自主路由工具、无需逐步提示并交付完整结果。ProofBid 的任务终点是“投标准备包已生成并通过验证”，不包含签章、外发或实际投递。
- 当前评分权重：Innovation & Operational Utility 40%；Architectural Discipline & Tech Stack 30%；Demo & Production Readiness 30%。

## 已核验的技术与提交要求

- 使用 Gemini 3.5 Flash 或更新模型；ProofBid 锁定稳定模型 ID `gemini-3.5-flash`。
- 使用至少一种 Google Agent Framework；ProofBid 使用 Google ADK `Agent + FunctionTool + Runner`。
- 使用至少一种 Google Cloud 基础设施服务；ProofBid 使用 Cloud Run Service、Cloud Run Job 和 Cloud Storage。
- 提交需包含项目说明、技术与数据来源、代码仓库、从零启动说明和架构图。
- Demo 不超过 4 分钟，必须实际展示应用运行及 Google Cloud 后端证明。
- Demo 视频必须公开托管于 YouTube 或 Vimeo；英文录制或提供英文字幕。
- 仓库可以公开或私有；私有仓库必须向官方指定评审账号开放。ProofBid 决策为公开 Apache-2.0 仓库。
- Hosted Project URL 不是绝对强制，但官方强烈建议；ProofBid 目标为公开 `.run.app` 合成演示。
- 参赛者必须拥有提交内容的必要权利，并对使用的既有代码、第三方依赖、数据和素材作真实披露。比赛期新增工作必须可识别，不得把旧产品换名冒充新项目。
- 提交材料、演示与评审访问必须在判断期保持可用；提前提交后不随意修改仓库、视频和演示内容。

## 仍需参赛人本人最终确认

- 居住地、年龄、雇佣关系、制裁地区及其他完整资格条款；
- 团队组成、奖金分配、税务与获奖材料使用许可；
- Devpost 提交页当天的字段、字符限制、评委邮箱和确认勾选项；
- 同一作品投其他赛事的具体兼容边界；
- Google Cloud Credits 申请结果、计费账号、配额与模型在隔离项目中的实际可用性。

## 本项目执行门禁

- 只使用合成或明确公开的数据；禁止真实客户、真实报价、联系人、凭据、内部路径和其他项目资产进入仓库或云端。
- `gemini-3.5-flash`、Cloud Run Job、Cloud Storage、公开 URL 和 Cloud Logging 必须以真实回执证明；本地 fake-model、SDK 构造、Dockerfile 或部署脚本不算云端验证。
- 公共演示仅开放 `complete_tender` 与 `blocked_missing_authorization` 两个内置夹具，不开放任意文件上传。
- 报名、Credits 申请、计费资源创建、公开 push、部署、视频发布和 Devpost 提交均需用户明确授权。
- 提交证据必须保留 commit/tag、容器与 Cloud revision digest、真实 Gemini provider receipt、Cloud Job execution ID、演示 URL、视频 URL/hash、提交截图、时间戳与确认邮件。
