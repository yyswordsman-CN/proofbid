# Google All Things Agentic — Rules Snapshot

> 快照日期：2026-08-26。用途：ProofBid 冻结与提交门禁。已复核官方 Rules、FAQ、最新提交检查表和自检建议；官方页面及最终 Devpost 表单始终优先于本文件。

## 官方入口与时间

- 赛事主页：https://allthingsagentichackathon.devpost.com/
- Rules：https://allthingsagentichackathon.devpost.com/rules
- Resources：https://allthingsagentichackathon.devpost.com/resources
- FAQ：https://allthingsagentichackathon.devpost.com/details/faqs
- 官方开发节奏：https://allthingsagentichackathon.devpost.com/updates/45652-how-to-plan-your-project
- 官方提交检查表：https://allthingsagentichackathon.devpost.com/updates/45853-one-week-to-go-run-this-checklist-before-you-submit
- 官方 Demo 自检建议：https://allthingsagentichackathon.devpost.com/updates/45852-give-your-project-a-self-check-pro-tips-inside
- 正式截止：2026-08-31 17:00 PDT，即北京时间 2026-09-01 08:00。
- 评审期：2026-09-01 09:00 PT 至 2026-10-01 23:45 PT；预计 2026-10-08 公布结果。
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
- 项目必须在 2026-08-03 至 2026-08-31 的 Submission Period 内新建。ProofBid 于 2026-08-19 建立独立项目，比赛期新增工作与既有经验边界记录在 `PREEXISTING_IP.md`。
- 可使用标准开发工具、框架、库、starter template 和 AI coding assistant；任何纳入提交的其他既有代码或工作必须如实披露。
- 提交需包含项目说明、技术与数据来源、代码仓库、从零启动说明和架构图。
- Demo 不超过 4 分钟，必须实际展示应用运行及 Google Cloud 后端证明。
- Demo 视频必须公开托管于 YouTube 或 Vimeo；英文录制或提供英文字幕。
- 官方提交建议要求前 10–15 秒展示产品开始工作，并允许剪除加载、等待和无信息片段；评分规则同时要求可信的 live execution。ProofBid 因此保留可核验的真实动作片段，并以 task/execution ID、Cloud 记录和 digest 证明剪辑前后连续性，不再把全片一镜到底作为官方门槛。
- 仓库可以公开或私有；私有仓库必须向官方指定评审账号开放。ProofBid 决策为公开 Apache-2.0 仓库。
- Hosted Project URL 不是绝对强制，但官方强烈建议；ProofBid 目标为公开 `.run.app` 合成演示。
- 参赛者必须拥有提交内容的必要权利，并对使用的既有代码、第三方依赖、数据和素材作真实披露。比赛期新增工作必须可识别，不得把旧产品换名冒充新项目。
- 截止前可保存草稿并多次修改；截止后 Devpost 提交锁定。仓库、视频和演示在评审期必须保持提交时版本，继续开发应使用独立分支或副本。

## 已取得的 ProofBid 外部证据

- 真实 `gemini-3.5-flash`、Google ADK FunctionTools、Vertex AI ADC、Cloud Run Service/Job、Cloud Storage、Cloud Logging、公开 `.run.app` 和公开仓库均已有项目内回执。
- Google All Things Agentic Hackathon USD 150 Credits 已批准并兑换；当前计费状态和有效期以 `PROJECT_CONTEXT.md` 与 `docs/evidence/2026-08-25-google-cloud-credits.md` 为准。
- 公开英文 Demo、匿名播放复验和本地 freeze commit/tag 已闭合；冻结引用尚未 push，Devpost 正式提交和最终回执仍未完成。以上状态不等于完成比赛提交。

## 提交当天由参赛人本人再次确认

- 居住地、年龄、雇佣关系、制裁地区及其他完整资格条款；
- 团队组成、奖金分配、税务与获奖材料使用许可；
- Devpost 提交页当天的字段、字符限制、评委邮箱和确认勾选项；
- 同一作品投其他赛事的具体兼容边界；
- 最终冻结时演示 URL、仓库、视频和 Google Cloud 证明的可访问性。

## 本项目执行门禁

- 只使用合成或明确公开的数据；禁止真实客户、真实报价、联系人、凭据、内部路径和其他项目资产进入仓库或云端。
- `gemini-3.5-flash`、Cloud Run Job、Cloud Storage、公开 URL 和 Cloud Logging 必须以真实回执证明；本地 fake-model、SDK 构造、Dockerfile 或部署脚本不算云端验证。
- 公共演示仅开放 `complete_tender` 与 `blocked_missing_authorization` 两个内置夹具，不开放任意文件上传。
- 新的真实 Cloud 任务、计费资源变更、公开 push、部署、创建 tag、视频发布和 Devpost 提交均需用户明确授权。
- 提交证据必须保留 commit/tag、容器与 Cloud revision digest、真实 Gemini provider receipt、Cloud Job execution ID、演示 URL、视频 URL/hash、提交截图、时间戳与确认邮件。
- 截止后不得更新提交分支、视频或演示；如需继续开发，使用独立分支或副本并保持冻结材料不变。
