# 最小 Google Planner 接入收尾记录

> 收尾日期：2026-08-22
> 证据范围：本地代码、合成输入、Fake Model/SDK 构造与本地测试
> 不包含：真实 Gemini 网络调用、Google Cloud 资源、部署或比赛提交

## 本轮完成

- 新增 vendor-neutral `TaskSpec`、`ExecutionPlan`、`PlanStep` 与 `ProviderReceipt`，并提供版本化 JSON Schema。
- 接入 Google ADK `Agent + App + Runner + InMemorySessionService` 与 Gemini Provider Adapter，固定模型 `gemini-3.5-flash`，提供显式 `proofbid google-run`。
- Planner 不注册执行工具，不接收招标正文、主体资料或目录正文；模型只生成结构化计划，本地策略通过后才放行原确定性 pipeline。
- Agentic 产物增加 `task_spec.json`、`execution_plan.json`、`planner_receipt.json`，与 Trace、result、manifest、ZIP 做 execution mode、task、digest 和语义交叉绑定。
- 补齐输出预检、输入漂移、认证后端、有限重试、异常 finish reason、路径与归档安全等 fail-closed 测试。

## 当前验证

- 2026-08-22：`.venv/bin/python -m pytest -q -ra`，结果 `42 passed`。
- 警告仅来自上游：google-genai 使用即将弃用的 `_UnionGenericAlias`；ADK 的 `BaseAgentConfig` 已标记弃用。
- 既有合成确定性运行保持：12 条要求、30 条证据、2 条 BOM、CNY 274000 目录硬件小计、6 个真实 blocker；产物完整性通过，业务门禁未通过且 `ready_for_submission=false`。
- 当前没有获授权的 Gemini API key 或 Google Cloud ADC，故没有真实 `model_version`、usage、finish reason、invocation id 等网络调用证据。
- 当前目录不是 Git 仓库，无法提供 commit、push、tag 或远端可见性证据。

## 优秀实践与可复用经验

1. **模型只规划，确定性链负责事实与执行。** ADK Agent 使用 `tools=[]` 和结构化输出；模型不能选择本机路径、执行 Shell/SQL/MCP、生成领域事实或直接写产物。
2. **请求最小化。** Planner 只接收目标、相对文件名、类型、大小和 source hash，不发送不可信正文，既降低提示注入面，也避免免费层或第三方服务接触敏感材料。
3. **计划是授权合同，不是自由文本。** 工具 allowlist、固定 canonical DAG、唯一 step id、依赖完整性、无环、步数上限和 TaskSpec digest 全部在本地复验；任一不符均不执行 pipeline。
4. **外部调用必须排在本地必败检查之后。** 输出目录、输入 manifest 和凭据先检查，再调用 Gemini，避免在注定失败时产生外部传输、费用或远端痕迹。
5. **证据包需要语义绑定，不能只做字节哈希。** Validator 重新解析三份 planning JSON，并交叉核对 task id、plan digest、receipt、Trace、result、manifest 和 execution mode。
6. **Agentic 与 deterministic 必须双向排他。** Agentic 缺 planning 证据失败，deterministic 夹带 planning 文件或 Planning Trace 也失败，防止剥离证据降级或把模型参与伪装成确定性执行。
7. **交付根目录和归档成员要按不可信输入处理。** 统一 delivery root、固定 basename、manifest/ZIP exact-set、普通文件类型、`0644`、跨平台文件名、NFC+casefold 唯一性和 symlink 门禁一起执行。
8. **失败路径也要无副作用。** 所有输出使用同目录随机 `O_EXCL` staging 后原子替换；Trace 使用 `O_NOFOLLOW`，避免可预测 `.tmp` 或符号链接覆写外部文件。

## 踩坑与规避方式

1. **ADK 主版本不能凭旧 pin 编码。** 项目原始 `google-adk>=1,<2` 与实际 2.x API 不一致；最终按官方 tag 和已安装运行时签名锁定 `google-adk==2.7.1`、`google-genai==2.18.1`。
2. **默认模型并不可靠。** `LlmAgent` 与显式 `Gemini()` 的默认值可能不同；Provider Adapter 必须明确写入固定 model id，回执也必须记录实际 model version。
3. **环境变量判断可能与 SDK 语义不一致。** `GOOGLE_GENAI_USE_ENTERPRISE` 与旧 Vertex 变量存在优先级和布尔解析差异；最终显式向 Gemini client 传递 backend，不能只在回执里推测认证模式。
4. **ADK final event 不是“见到第一个就退出”。** 必须完整消费事件流、过滤 root agent、拼接非 thought 文本，并跨事件聚合错误、usage、model version 和 finish reason。
5. **结构化 JSON 可解析不等于模型成功。** 只有规范化 `finish_reason=STOP` 才接受；`MAX_TOKENS`、`SAFETY`、`RECITATION` 等即使留下可解析 JSON 也应失败关闭。
6. **计划存在不等于计划驱动了执行。** 若 executor 仍固定执行，计划必须与 canonical 顺序和依赖精确一致；否则审计证据会与真实行为背离。
7. **manifest 哈希无法证明证据关系。** 若不做 schema 和跨文件 binding，篡改后的 planning 文件仍可被新 manifest “合法签入”。
8. **Mapping 输入容易产生旁路。** 省略字段、A/B 跨目录拼包、Trace 重定向、核心 payload 不入 ZIP 等都需要由 manifest.parent 唯一根和固定文件集合阻断。
9. **跨平台归档风险不止 `../`。** ZIP Unix symlink、反斜杠、Windows 非法字符/设备名、大小写和 Unicode 归一化碰撞都可能在另一操作系统解压时覆盖已验证文件。
10. **渲染前后都要检查 symlink。** 只在 Validator 事后报告太晚，敏感外部文件可能已被读入 ZIP；Renderer 写前、hash 前和归档前都必须 fail closed。
11. **可预测临时文件是写入漏洞。** `result.json.tmp -> 外部文件` 会在校验前覆写目标；应使用 `mkstemp/O_EXCL` 随机 staging，且测试必须断言外部 sentinel 未变化。
12. **安全回归应拆成独立测试。** 把 symlink 场景追加进已创建目标文件的测试，会先触发 `FileExistsError`，并没有真正覆盖待测防线。

## 接力点

唯一下一动作保持不变：获得明确授权的 Gemini API key，或配置合法的 Google Cloud ADC 后，只对 `examples/synthetic_tender` 执行一次真实 `google-run`。

真实 smoke 必须同时保存脱敏证据：UTC、固定请求模型、实际 `model_version`、usage、finish reason、invocation id、请求/响应/计划 digest、SDK/ADK 版本、Pydantic Schema 校验、本地计划策略和最终产物校验。无凭据、fallback、Fake Model 或只有 SDK 构造均不得记为成功。

在凭据缺失期间可以继续离线开发和运行 `proofbid run`，但不得声称真实 Gemini、Google Cloud 或参赛部署已验证。免费 API 层只允许合成数据；不得购买共享 Key、使用来路不明的代理，或把真实投标资料上传到未批准服务。
