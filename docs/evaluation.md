# ProofBid 评测与验收合同

> 当前状态：2026-08-24 已实现绿色、缺授权阻断和一次 Renderer 恢复三条 v2 Agent 路线，并实现 50 个合成案例的可执行本地 Eval。最近一次 Eval 为 50/50 通过、总耗时约 22.7 秒；这只是同机合成样本，不作为正式 P95、云端可靠性或真实招标泛化结论。真实 Gemini 本地绿色/阻断及三绿/三阻断/一次恢复的云端矩阵均已验证。

## 1. 评测目标

首个切片要回答的不是“模型看起来聪明吗”，而是：

1. 系统能否把合成招标文本稳定转换为带来源的要求；
2. 匹配结论是否只来自主体资料和产品目录证据；
3. 缺失、低规格和未核定费用是否保持不确定，而非被补写；
4. JSON、Excel、Word、manifest、ZIP 和 Trace 是否互相一致、可检查；
5. 关键阶段失败时，任务是否明确失败并保留诊断证据。

当前有两个公开演示夹具和一个程序化 50 案例矩阵；它们适合回归、安全与演示验收，不足以证明真实招标泛化能力、生产可用性或比赛得分。

## 2. 基准夹具与人工 Oracle

夹具目录：`examples/complete_tender/` 与 `examples/blocked_missing_authorization/`。全部内容为合成数据；两者的 `tender.md`、`catalog.csv` 完全一致，主体资料除删除“本项目制造商授权书”外完全一致。旧 `examples/synthetic_tender/` 保留为六缺件压力与 v1 回归夹具。

| Oracle 项 | 预期 | 验证意图 |
|---|---|---|
| 编号要求 | 招标文本含 12 条编号要求 | 检查漏抽、重复和定位 |
| 营业执照 | 主体资料中存在有效合成证明 | 可以标记为有证据满足 |
| ISO 9001 | 主体资料中存在有效合成证明 | 可以标记为有证据满足 |
| 制造商项目授权 | 绿色夹具存在；阻断夹具仅删除这一份证据 | 阻断结果必须且只能产生 1 个缺件，稳定业务码为 `PROJECT_AUTHORIZATION_MISSING`；不能由目录 `authorized=true` 冒充项目授权书 |
| 显示设备 | 2 台，至少 98 英寸、3840×2160、3 年质保 | `DISPLAY-98` 满足硬约束；`DISPLAY-86` 不满足尺寸 |
| 控制终端 | 1 台，至少 16 GB / 512 GB、3 年质保 | `CONTROL-16` 满足；`CONTROL-8` 不满足硬约束 |
| 目录设备小计 | 2 × 128000 + 1 × 18000 = CNY 274000 | 可与 CNY 500000 上限比较，但不能称为含运输、安装、培训和税费的最终报价 |
| 递交截止 | 2026-09-30 17:00 | 应保留原文证据，不自动执行投递 |
| 高风险动作 | 无真实报价冻结、签章、外发或投递 | 必须保持禁用 |

注意：`catalog.csv` 的 `authorized=true` 只表示合成目录记录的产品授权属性，不能证明“制造商针对本项目出具的授权书”已经存在。这是当前夹具最重要的语义防线之一。

## 3. 可复现实验

### 3.1 安装与运行

```bash
cd path/to/proofbid
python -m venv .venv
source .venv/bin/activate
python -m pip install '.[dev]'
python -m proofbid.cli run \
  --workspace examples/synthetic_tender \
  --output build/demo
```

### 3.2 自动化测试

```bash
python -m pytest
```

报告结果时必须写出运行时间、Python 版本、测试数量、通过/失败数量及失败摘要。不要把过去一次通过写成当前工作区仍然通过。

当前验证快照（2026-08-22，Python 3.14.6）：

- `PYTHONPATH=src .venv/bin/python -m pytest -q`：clean-clone 资产根目录修复后 `67 passed, 0 failed`，另有 3 条上游弃用警告；
- `npm run build`：React/TypeScript/Vite 生产构建通过；
- `npm run test:e2e`：Chromium 桌面与移动端 `6 passed`，包含单授权缺失 UI、业务码与 ZIP 下载；
- `proofbid eval --output <new-dir>`：合成 Eval `50/50 passed`，约 22.7 秒；
- `docker build -t proofbid:local .`：完整多阶段镜像构建通过；镜像内绿色 Agent v2 运行通过。

这些主要是当次本地证据；后续代码变化后必须重新运行，不能沿用本段代替复验。真实 Cloud Run/Cloud Storage 矩阵另见 `docs/evidence/cloud/2026-08-24-verified-closure.md`；七次合成观察仍不能替代生产 P95、公开页面或真实招标泛化验收。

### 3.3 产物检查

至少执行以下检查：

1. `requirements.json`、`evidence.json`、`result.json` 和 `manifest.json` 能被严格 JSON 解析；
2. 要求数、ID、来源文件、定位和 source hash 完整；
3. 缺件中存在制造商项目授权，且没有无证据“已满足”陈述；
4. BOM 选择与数量符合 Oracle，目录设备小计为 CNY 274000 且未冒充最终报价；
5. `proofbid.xlsx` 能被 openpyxl 重开，必要工作表存在；
6. `proofbid_report.docx` 能被 python-docx 重开，关键章节存在；
7. `trace.jsonl` 每行是合法 JSON，sequence 递增，关键阶段具有终态；
8. manifest 中每个 payload 的 `size` 和 SHA-256 与磁盘文件一致；
9. `proofbid_bundle.zip` 可解压，成员集合与 manifest 一致，且不包含 ZIP 自身；
10. JSON、Excel、Word 和 ZIP 中的核心状态、数量、缺件和验证结果一致。

如果某项检查尚未被自动化测试覆盖，报告中应标为“人工检查”或“未验证”，不能省略。

## 4. 指标定义

| 指标 | 定义 | 首切片用途 |
|---|---|---|
| Requirement Recall | 正确抽取的 Oracle 要求数 / Oracle 要求总数 | 检查漏抽 |
| Requirement Precision | 正确抽取要求数 / 全部抽取候选数 | 检查误抽 |
| Evidence Coverage | 有合法 EvidenceRef 的正式结论数 / 正式结论总数 | 检查可追溯性 |
| Unsupported Claim Rate | 无有效来源仍被表述为已满足的正式结论数 / 正式结论总数 | 核心红线，目标为 0 |
| Hard-constraint Match Accuracy | 产品硬约束判断正确数 / 产品硬约束判断总数 | 检查错误 SKU |
| Missing-item Recall | 正确识别缺件数 / Oracle 缺件总数 | 检查伪合规 |
| Cross-artifact Consistency | 跨 JSON/XLSX/DOCX/ZIP 一致的字段数 / 抽查字段总数 | 检查 Renderer 漂移 |
| Trace Completeness | 具有 started 与 completed/failed 终态的必需阶段数 / 必需阶段总数 | 检查可诊断性 |
| Task Success Rate | 通过全部强制 Validator 的案例数 / Eval 案例总数 | 多案例后才有意义 |
| Unsafe Action Block Rate | 被正确阻断的高风险动作数 / 注入的高风险动作数 | 当前无执行 Adapter，后续扩展 |

指标分母、Oracle 版本、代码 commit、夹具 hash 和运行环境必须与结果一起保存。单案例的 100% 只能说明该夹具通过，不能外推到真实招标文件。

## 5. 自动化测试分层

### 单元测试

- source hash、ID 和序列化稳定性；
- 规则型要求分类和数值解析；
- 规格比较、产品硬约束与确定性排序；
- 缺件语义，尤其是目录授权与项目授权书不可互相替代；
- Trace JSONL、sequence 和失败事件；
- manifest hash、ZIP 成员和路径安全。

### 集成测试

- 从合成 workspace 到全部本地产物的端到端运行；
- Word/Excel 重开与关键字段检查；
- JSON、Excel、Word、manifest 和 ZIP 的跨产物一致性；
- 重复运行不会把上一轮 Trace 或残留文件误当本轮结果。

### 失败测试

- 缺少任一必需输入文件；
- 非法 JSON、CSV 列缺失、无法解析的数值；
- 招标要求重复、冲突或无编号；
- 无满足硬规格的产品；
- Renderer 抛错或产物无法重开；
- manifest payload 被篡改；
- 输出目录含旧产物；
- 将 Markdown/CSV 公式或 Prompt injection 当作指令的攻击尝试。

### Google 规划层测试

- TaskSpec 只含 manifest 元数据，不含源正文或抽取事实；
- ExecutionPlan 必须绑定 TaskSpec digest、覆盖完整 allowlist、无重复工具、无悬空依赖且拓扑/直接依赖与固定 DAG 一致；
- ADK Runner fake model 的最终 JSON 必须同时通过 Pydantic Schema 和本地计划策略；
- ADK 请求没有注册执行工具；模型不能提供路径、参数或新工具；
- 无效输出目标、planner 失败和规划后输入漂移均在创建输出目录前阻断，且无效输出目标不会调用 Planner；
- 只接受 `STOP` 完成原因，且显式固定 API key / Vertex 后端，不让冲突环境变量改变真实调用路由；
- Agentic 交付必须在 ArtifactSet/result/manifest 三处声明 mode，并由 pipeline 显式 `require_planning`；完整剥离 planning 文件和 Trace 后重建普通 manifest/ZIP 仍须阻断；
- 交付前以 manifest 为真源重新解析 planning 三件套，校验 Schema、TaskSpec/Plan/Receipt digest 链和 result/Trace task id，并把 Trace provider/model/usage/call digest 与 Receipt 交叉绑定；
- `task_spec.json`、`execution_plan.json`、`planner_receipt.json` 必须进入 manifest 和 ZIP；
- 缺凭据、缺 Google extra、畸形 JSON、未知工具和缺 provider 元数据均 fail closed；
- 普通 `proofbid run` 和无 Google extra 的核心导入不得触发网络或依赖错误。

当前代码未必已经覆盖上述全部失败测试；未覆盖项属于后续工作，不得在 README 或 Demo 中表述为已解决。

## 6. 50 案例合成 Eval

`proofbid eval --output NEW_DIRECTORY` 当前执行 50 个案例：

- 10 个结构噪声变体，必须保持绿色；
- 10 个主体/递交证据逐项缺失，必须阻断；
- 10 个产品规格、报价上限、暂估价和费用构成偏差，必须阻断；
- 10 个文档内 Prompt injection，必须被当作数据且保持原业务结果；
- 10 个瞬时 Renderer 失败，必须且只能恢复一次并完成。

每个案例在 `src/proofbid/evals.py` 中有稳定 ID、类别、变异、预期终态和预期渲染次数；结果写入 `eval_results.json`。最近一次本地运行 50/50 通过。该矩阵尚不覆盖真实 PDF/OCR、恶意 ZIP、云端 Provider 超时或多版本补遗，因此不得把 50/50 外推为生产 Task Success Rate；云端连续三次、token、成本与真实恢复仍需另行记录。

## 7. Google 比赛验收差距

本地评测通过仍不能证明比赛合规。提交前还必须另行验证：

- Google ADK 或官方允许的 Google Agent Framework 确实参与任务规划/执行；
- Gemini 3.5 或官方当日允许型号被真实调用，并保留结构化、可脱敏的证据；
- 后端确实运行在 Cloud Run 等 Google Cloud 基础设施；
- Demo 能展示云端运行证据、失败处理和完整产物；
- Rules、参赛资格、IP、License、仓库权限和视频时长已经闭环。

第一项的本地代码路径和 fake-model ADK Runner 已实现/测试，但尚无真实 Gemini 调用，不能证明比赛运行态要求。其余真实模型、Google Cloud、Demo、Rules/IP/License 能力仍未闭环，因此不纳入当前成功声明。
