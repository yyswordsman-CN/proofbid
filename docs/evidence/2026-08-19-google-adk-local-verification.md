# Google ADK Planner 本地验证证据

> 验证时间：2026-08-19T08:06:24Z。范围：本地代码、固定依赖、SDK 接口、fake-model ADK Runner、计划策略与 fail-closed 行为。该记录不包含 Gemini 真实网络调用证据。

## 环境

- macOS / Python 3.14.6；
- `google-adk==2.7.1`；
- `google-genai==2.18.1`；
- `pydantic==2.13.4`；
- `pytest==9.1.1`。

依赖版本来自项目隔离 `.venv` 的实际 metadata。Google ADK 2.7.1 官方要求 `google-genai>=2.12.1,<3`，当前组合在该范围内。官方入口：

- https://github.com/google/adk-python/releases/tag/v2.7.1
- https://pypi.org/project/google-adk/2.7.1/
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash

## 已执行验证

### 完整 Google 环境

```bash
.venv/bin/python -VV
.venv/bin/python -m pytest -q
```

结果：Python 3.14.6，`42 passed, 0 failed`。出现 2 条上游 deprecation warning：Google GenAI 对 Python 私有 typing alias 的引用，以及 ADK `BaseAgentConfig` 的弃用提示；本轮没有把 warning 当作功能通过证明，也未发现测试失败。

项目随后以普通 wheel 方式重装到 `.venv`，无需 `PYTHONPATH` 即可导入 `proofbid` 并执行已安装的 `proofbid --help` 与确定性合成夹具命令。未采用 editable 安装作为交付验证依据；当前 macOS / Python 3.14 会忽略带隐藏文件标记的 editable `.pth`。

覆盖内容包括：

- Google ADK `Agent + App + Runner + InMemorySessionService` 实际事件流；
- Pydantic `output_schema` 最终 JSON 二次解析；
- 本地 allowlist、完整 DAG、拓扑、直接依赖和 TaskSpec digest 门禁；
- 固定 `Gemini(model="gemini-3.5-flash")`、API key / Vertex 后端和有限重试对象构造（不发起网络调用）；
- 非 `STOP` finish reason 拒绝，无效输出目标在 Planner 调用前拒绝；
- 计划/回执/TaskSpec 进入 manifest 与 ZIP；
- planning 三件套以 manifest 为真源重新解析，并复验 TaskSpec/Plan/Receipt digest、result/Trace task id 及 Trace/Receipt provider metadata；
- `execution_mode=agentic` 在 ArtifactSet/result/manifest 三处一致；agentic 必须同时带完整 planning 三件套与 Planning Trace，deterministic 不得夹带任一 planning marker；
- Validator 从 manifest 对应的固定 `output_dir/trace.jsonl` 读取审计记录，Mapping 不能用空值或外部路径隐藏 Planning Trace；显式 `require_planning` 会阻断完整证据剥离后的降级包；
- `manifest.parent` 是唯一 delivery root，所有固定 artifact 与 supplemental 路径必须同根且使用固定 basename；Mapping 核心 payload omission、跨目录拼接及文件系统 symlink 均被 blocker 拒绝；
- manifest/ZIP 对 5 个核心 payload、按合同存在的 Trace、agentic 三件套与显式 supplemental 执行同一 exact-set；ZIP 每个成员必须是 canonical Unix regular `0644` 文件，内部 symlink metadata 同样被拒绝；
- supplemental、manifest 与 ZIP 成员名共用 POSIX/Windows flat-name 规则，并以 NFC+casefold portable key 拒绝非法字符、设备保留名、固定/planning 名称伪装和跨平台大小写/归一化碰撞；
- Renderer 在写入前拒绝 output root 中的 symlink；JSON/XLSX/DOCX/Trace/ZIP 与 planning JSON 全部使用同目录随机 O_EXCL staging 后原子替换，Trace append 使用 O_NOFOLLOW。staging/Trace symlink 失败注入不会改写外部 sentinel，也不会生成 manifest/ZIP；
- planner 失败和规划后输入漂移均在创建输出目录前阻断；
- JSON Schema 与 Python 合同一致性；
- 原 deterministic pipeline 回归。

fake model 的 ADK 请求中 `tools_dict == {}`。它返回带 `model_version`、usage 和 finish reason 的合成事件，仅用于验证 ADK Runner/事件提取/Schema 代码路径，不能冒充真实 Gemini 回执。

### 无 Google extra 的离线兼容

```bash
PYTHONPATH=src python3 -m pytest -q
```

结果：`36 passed, 0 failed`；依赖 Google ADK 与 `jsonschema` 的可选测试按设计跳过。核心包、普通 `proofbid run` 和 Gemini 配置解析不要求安装 Google extra。

### 已安装 CLI 冒烟

项目以普通 wheel 重装后，`proofbid` 从 `.venv` 的 `site-packages` 导入；关键安装文件与工作区源码 SHA-256 一致，`proofbid --help` 同时显示 `run` 与 `google-run`。已安装入口运行合成夹具得到 12 条要求、30 条证据、2 条 BOM、CNY 274000 目录硬件小计和 6 个 blocker；`artifact_integrity_passed=true`、`ready_for_submission=false`。最终 manifest 含 6 个 payload，ZIP 含 7 个成员（含 manifest），全部 size、SHA-256、CRC、exact-set 及 regular `0644` member type 复验通过。

### 缺凭据 fail-closed

在没有 `GEMINI_API_KEY`、`GOOGLE_API_KEY` 或 Google Cloud 配置时执行 `google-run`：

- 退出码：2；
- reason code：`PROVIDER_CONFIGURATION_INVALID`；
- stdout：空；
- 输出目录：未创建。

### 缺 Google extra fail-closed

在系统 Python 环境仅设置合成 sentinel key、但未安装 Google extra 时执行 `google-run`：

- 退出码：2；
- reason code：`PROVIDER_DEPENDENCY_MISSING`；
- 输出目录：未创建；
- 错误输出未包含 sentinel key。

## 未验证

- 没有可用且获授权的 Gemini API key 或 Google Cloud ADC 项目配置，未发起真实 Gemini 网络请求；
- 因此没有真实 provider `model_version`、usage、finish reason、invocation id 或服务端交互 ID；
- 尚未验证 Vertex/Enterprise AI、Cloud Run、Cloud Storage、Secret Manager、Cloud Logging/Trace 或计费；
- 尚未把本地固定安全 DAG 的最小 Planner 结果外推为通用 Agent 任务完成能力。

真实验证必须使用合成夹具和显式 `google-run`，成功后另存一次脱敏 `planner_receipt.json`、最终 manifest/ZIP 哈希与命令结果；不得把本文件改写为真实调用证据。
