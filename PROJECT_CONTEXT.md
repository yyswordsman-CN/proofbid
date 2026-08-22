# PROJECT_CONTEXT — ProofBid

> Last updated: 2026-08-22

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
- `proofbid-cloud-evidence` is implemented to collect and fail-closed reconcile revision/image, execution, task state, provider/usage/FunctionTool evidence, GCS generation/checksums, manifest/ZIP SHA-256 and redacted log timestamps. Raw downloads are ignored; cloud execution remains unverified.
- The English React/Vite workbench implements the two public cases, task route, tool timeline, evidence/validation/artifact views, readiness, provider/cloud proof, and ZIP download. Arbitrary upload is not exposed.
- A versioned English Mermaid architecture source now exports to a reviewed SVG and exact 1920×1080 PNG using pinned Mermaid CLI 11.16.0. A clean-clone verifier covers Python 3.12/Node 22 installs, tests, Eval, frontend, Playwright, Workbench API/download, Docker build, and container green route.
- The programmatic Eval matrix contains and executes 50 synthetic cases: 10 structure, 10 missing evidence, 10 product/pricing, 10 prompt injection, and 10 bounded renderer recovery.

## Verification completed in this workspace

- `PYTHONPATH=src .venv/bin/python -m pytest -q`: **67 passed**, 0 failed; three upstream deprecation warnings. V2-specific tests include undeclared tools, out-of-order calls, duplicate completion, input drift, wrong terminal branch, green/blocked/recovery routes, fixture single-variable invariants, stable missing-item reason codes, API state, FunctionTool call IDs, real-receipt rebinding, scripted-marker rejection, fixture allowlisting, evidence-summary redaction, and installed-CLI asset-root resolution.
- Three direct v2 routes: green `completed`, authorization case `blocked`, injected render failure recovered exactly once and `completed`; all artifact integrity gates passed.
- `proofbid eval`: **50/50 passed** in about 22.7 seconds on one local synthetic run. This is not a P95 or production reliability claim.
- `npm run build`: production React build passed.
- Playwright real Chromium at 1440×1000 and 390×844: **6/6 passed** after the single-authorization UI change, including visible missing count, stable reason code and blocked ZIP download.
- Fresh green and blocked Word/Excel files were reopened with LibreOffice and exported to PDF. Both Word reports rendered as two landscape pages; the green/blocked first pages and workbook summaries were visually inspected. The green report wording was corrected to reflect evidenced quote inclusions, and workbook print settings reduced horizontal pagination.
- `bash -n infra/cloud-shell-deploy.sh`: passed.
- `docker build -t proofbid:local .`: multi-stage image built successfully after transient registry retries.
- The non-root built image ran the complete tender through Agent v2 and returned `completed`, both readiness flags `true`, 10 tool calls, and artifact integrity passed.
- Repository scan found no populated API keys/private keys, user name, or absolute local project path.

## Evidence not yet obtained

- No authorized Gemini credential or Vertex AI ADC project is configured in this workspace. `google-agent-run` code and FunctionTools are locally validated, but no real `gemini-3.5-flash` provider event, usage, finish reason, or invocation ID has been captured.
- No isolated Google Cloud project, billing/Credits result, Artifact Registry image, Cloud Run Service/Job, GCS bucket, Cloud Logging evidence, revision digest, execution ID, or public `.run.app` URL has been created or verified.
- No green/blocked case has been run three times in Google Cloud; no cloud token/cost sample exists.
- No public GitHub repository, commit/tag, push, video, Devpost submission, or external receipt exists.

## Locked scope

- Main category: The Taskmaster; additional targets are Individual/Hobbyist and Best Architectural Design.
- Public demo: English, synthetic, only two built-in fixtures, Apache-2.0.
- Infrastructure: Cloud Run Service + Cloud Run Job + Cloud Storage + Vertex AI ADC. No Firestore, Pub/Sub, multi-agent system, PDF/OCR, signing, sending, pricing freeze, or submission.
- Real cloud resource creation, public push, video publication, and Devpost submission require explicit user authorization.

## Unique NEXT

After the owner authorizes and configures an isolated Google Cloud competition project, run `infra/cloud-shell-deploy.sh`, then capture one real `complete_tender` Job end-to-end. Success requires all of the following in the same evidence chain:

1. public Service returns 202 and records a real Cloud execution ID;
2. Job reaches `completed` without a follow-up prompt;
3. provider receipt identifies real `gemini-3.5-flash`, usage, finish reason and invocation ID;
4. both readiness flags are `true`, high-risk actions remain locked, and bundle download passes;
5. GCS hashes, Cloud revision/image digest and Cloud Logging timestamps are retained;
6. repeat green and blocked cases three times each before recording latency/token/cost samples.
