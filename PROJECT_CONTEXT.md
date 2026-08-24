# PROJECT_CONTEXT — ProofBid

> Last updated: 2026-08-24

## Current implementation

- The independent Git repository now has two evidence-preserving baseline commits: `699a6f5` records the pre-fix code baseline and `7a4c744` records its local verification. No remote, push, tag, or public repository exists yet.
- The project is Apache-2.0 licensed with `THIRD_PARTY_NOTICES.md` and an updated competition/IP snapshot.
- The original deterministic v1 vertical slice remains intact for regression.
- Two public-safe synthetic fixtures exist:
  - `complete_tender`: 12/12 requirements matched, 63 evidence refs, 2 BOM lines, CNY 274000 catalog subtotal, zero missing items, both readiness flags `true`.
  - `blocked_missing_authorization`: identical tender/catalog and otherwise identical bidder evidence to the green case, with only the project authorization removed; exactly one `PROJECT_AUTHORIZATION_MISSING` item, both readiness flags `false`, and a validated ZIP still delivered.
- `MissingItem.reason_code` is a required versioned contract field. Blocking readiness uses stable business codes rather than task-specific missing-item IDs. The old `synthetic_tender` remains the six-gap pressure/regression fixture.
- `ReadinessDecision` now binds `ready_for_human_review`, `ready_for_submission`, `submission_executed=false`, `high_risk_actions_locked=true`, and blocking reason codes across result and run summaries.
- Agent v2 is implemented as a server-bound state machine with real Google ADK `FunctionTool` registration. Gemini may choose bounded tool order, the deterministic terminal branch, and one legal renderer retry; it cannot supply paths, facts, prices, SQL, shell, URLs, or submission actions.
- V2 deliveries include `agent_run.json` and `tool_receipts.jsonl` with model/usage/invocation fields, tool/result digest chain, reason codes, durations, retry relation, and nullable ADK `function_call_id`. Real mode requires a unique non-null call ID on every FunctionTool receipt.
- Real Gemini mode now replaces provisional local planning metadata across `planner_receipt.json`, Trace, and `agent_run.json` before final rendering. Its acceptance gate requires `google.gemini`, Vertex AI ADC, configured `gemini-3.5-flash`, observed model version, `STOP`, non-zero usage, invocation ID and FunctionTool IDs, followed by a recursive scripted-fallback scan of the package.
- FastAPI implements `POST /api/v1/tasks` (202), status polling, validated-bundle gate, and non-invoking health endpoint. Local and GCS task stores share the same contract.
- Cloud Run Jobs v2 execution, GCS upload/download, a same-image Job worker, separate runtime service accounts, seven-day task lifecycle, scale-to-zero limits, Dockerfile, and Cloud Shell deployment script are implemented.
- Cloud deployment now starts with a green-only fixture allowlist, binds the full commit SHA through `PROOFBID_BUILD_VERSION`, emits structured lifecycle events, and provides separate administrator scripts to open the blocked fixture and inject one renderer failure.
- `proofbid-cloud-evidence` is implemented to collect and fail-closed reconcile revision/image digest, execution, task state, provider/usage/FunctionTool evidence, GCS generation/checksums, Service/GCS ZIP SHA-256 and redacted log timestamps. Raw downloads are ignored; the first green cloud execution is verified below.
- The English React/Vite workbench implements the two public cases, task route, tool timeline, evidence/validation/artifact views, readiness, provider/cloud proof, and ZIP download. Arbitrary upload is not exposed.
- A versioned English Mermaid architecture source now exports to a reviewed SVG and exact 1920×1080 PNG using pinned Mermaid CLI 11.16.0. A clean-clone verifier covers Python 3.12/Node 22 installs, tests, Eval, frontend, Playwright, Workbench API/download, Docker build, and container green route.
- The programmatic Eval matrix contains and executes 50 synthetic cases: 10 structure, 10 missing evidence, 10 product/pricing, 10 prompt injection, and 10 bounded renderer recovery.

## Verification completed in this workspace

- `PYTHONPATH=src .venv/bin/python -m pytest -q`: **69 passed**, 0 failed; three upstream deprecation warnings. V2-specific tests include undeclared tools, out-of-order calls, duplicate completion, input drift, wrong terminal branch, green/blocked/recovery routes, fixture single-variable invariants, stable missing-item reason codes, API state, FunctionTool call IDs, real-receipt rebinding, scripted-marker rejection, fixture allowlisting, evidence-summary redaction, revision digest extraction, installed-CLI asset-root resolution, and real-agent TaskSpec input serialization.
- Google Cloud CLI 581.0.0 is installed. The isolated project `proofbid-agentic-yys-260822` has billing and Vertex AI enabled; user auth and Vertex ADC are configured with this project as quota project.
- Commit `7f183aa` passed real local `gemini-3.5-flash` + ADK FunctionTool execution for both public fixtures. Green reached `completed` with 1,650 tokens; blocked reached `blocked` with one `PROJECT_AUTHORIZATION_MISSING` item and 1,740 tokens. Both reported `google.gemini`, Vertex AI ADC, `STOP`, real invocation IDs, 10/10 unique non-null FunctionTool call IDs, no scripted marker, locked high-risk actions, and integrity-validated ZIPs. See `docs/evidence/2026-08-24-real-gemini-functiontools.md`.
- Commit `704dbb6` is deployed in Cloud Run revision `proofbid-00002-jq7` with digest `sha256:17bbebcf2c3511b187279ee20cea9ec6359a6a6e763f66cfc0bbc056ce5c8aca`. Green task `task-1e219418489b4e1880f8` returned 202, ran Job execution `proofbid-agent-k2bfk`, called real `gemini-3.5-flash` through 10 ADK FunctionTools, reached `completed`, and delivered an integrity-validated ZIP. The Service download and GCS object both hash to `dd99b39ce8a9a007545d07b74d4e0e919a93c24c89a79f300532094422515c24`; build/revision, provider-manifest, FunctionTool IDs and five structured lifecycle log events reconcile. See `docs/evidence/cloud/task-1e219418489b4e1880f8.md`.
- Three direct v2 routes: green `completed`, authorization case `blocked`, injected render failure recovered exactly once and `completed`; all artifact integrity gates passed.
- `proofbid eval`: **50/50 passed** in about 22.7 seconds on one local synthetic run. This is not a P95 or production reliability claim.
- `npm run build`: production React build passed.
- Playwright real Chromium at 1440×1000 and 390×844: **6/6 passed** after the single-authorization UI change, including visible missing count, stable reason code and blocked ZIP download.
- Fresh green and blocked Word/Excel files were reopened with LibreOffice and exported to PDF. Both Word reports rendered as two landscape pages; the green/blocked first pages and workbook summaries were visually inspected. The green report wording was corrected to reflect evidenced quote inclusions, and workbook print settings reduced horizontal pagination.
- `bash -n infra/cloud-shell-deploy.sh`: passed.
- `docker build -t proofbid:local .`: multi-stage image built successfully after transient registry retries.
- The non-root built image ran the complete tender through Agent v2 and returned `completed`, both readiness flags `true`, 10 tool calls, and artifact integrity passed.
- A fresh local Git clone of commit `97da579` passed Python 3.12.13 dependency installation, 67 tests, 50/50 Eval, Node 22.22.3 install/build, 6/6 Playwright, Workbench health/202/poll/download, Docker build, and a non-root container green route. The first attempt exposed and led to fixing installed-CLI asset-root resolution. Public HTTPS clone verification remains pending.
- Repository scan found no populated API keys/private keys, user name, or absolute local project path.

## Evidence not yet obtained

- The $150 Credits request is submitted and awaiting review; approval and redemption are not yet evidenced.
- Only one post-fix green case has completed and reconciled in Google Cloud. The required totals of three green and three blocked cases, plus one real renderer-recovery route, are not yet complete; no aggregate cloud latency/cost sample exists.
- Local commits exist and preserve the baseline/fix evidence chain. No public GitHub repository, remote push, submission tag, video, Devpost submission, or external success receipt exists.
- Public-repository preflight passed for secrets, absolute user paths, tracked size, failure-injection exposure, license, IP disclosure and notices. GitHub publication remains blocked because the active `gh` token is invalid and the owner did not complete the device authorization before it expired.

## Locked scope

- Main category: The Taskmaster; additional targets are Individual/Hobbyist and Best Architectural Design.
- Public demo: English, synthetic, only two built-in fixtures, Apache-2.0.
- Infrastructure: Cloud Run Service + Cloud Run Job + Cloud Storage + Vertex AI ADC. No Firestore, Pub/Sub, multi-agent system, PDF/OCR, signing, sending, pricing freeze, or submission.
- Real cloud resource creation, public push, video publication, and Devpost submission require explicit user authorization.

## Unique NEXT

The real-provider gate and first post-fix cloud-green closure are complete. Next keep the deployment green-only and capture two more independently reconciled `complete_tender` Cloud Run Job executions. Then open only `blocked_missing_authorization`, capture three blocked executions, and finally run one administrator-only renderer-recovery execution. Every run must retain task/execution IDs, provider receipt, FunctionTool IDs, terminal state, Service/GCS ZIP hash equality, revision/image digest and Cloud Logging timestamps before aggregate latency/token/cost reporting.
