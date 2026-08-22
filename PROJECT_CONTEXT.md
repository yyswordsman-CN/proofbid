# PROJECT_CONTEXT — ProofBid

> Last updated: 2026-08-22

## Current implementation

- The directory is now an independent Git repository on unborn branch `main`; no commit, remote, push, tag, or public repository exists yet.
- The project is Apache-2.0 licensed with `THIRD_PARTY_NOTICES.md` and an updated competition/IP snapshot.
- The original deterministic v1 vertical slice remains intact for regression.
- Two public-safe synthetic fixtures exist:
  - `complete_tender`: 12/12 requirements matched, 63 evidence refs, 2 BOM lines, CNY 274000 catalog subtotal, zero missing items, both readiness flags `true`.
  - `blocked_missing_authorization`: missing project authorization remains a truthful blocker; both readiness flags `false`; a validated missing-item ZIP is still delivered.
- `ReadinessDecision` now binds `ready_for_human_review`, `ready_for_submission`, `submission_executed=false`, `high_risk_actions_locked=true`, and blocking reason codes across result and run summaries.
- Agent v2 is implemented as a server-bound state machine with real Google ADK `FunctionTool` registration. Gemini may choose bounded tool order, the deterministic terminal branch, and one legal renderer retry; it cannot supply paths, facts, prices, SQL, shell, URLs, or submission actions.
- V2 deliveries include `agent_run.json` and `tool_receipts.jsonl` with model/usage/invocation fields, tool/result digest chain, reason codes, durations, and retry relation. They do not contain secrets, source body, full prompt, or hidden reasoning.
- FastAPI implements `POST /api/v1/tasks` (202), status polling, validated-bundle gate, and non-invoking health endpoint. Local and GCS task stores share the same contract.
- Cloud Run Jobs v2 execution, GCS upload/download, a same-image Job worker, separate runtime service accounts, seven-day task lifecycle, scale-to-zero limits, Dockerfile, and Cloud Shell deployment script are implemented.
- The English React/Vite workbench implements the two public cases, task route, tool timeline, evidence/validation/artifact views, readiness, provider/cloud proof, and ZIP download. Arbitrary upload is not exposed.
- The programmatic Eval matrix contains and executes 50 synthetic cases: 10 structure, 10 missing evidence, 10 product/pricing, 10 prompt injection, and 10 bounded renderer recovery.

## Verification completed in this workspace

- `PYTHONPATH=src .venv/bin/python -m pytest -q`: **55 passed**, 0 failed; three upstream deprecation warnings. V2-specific tests include undeclared tools, out-of-order calls, duplicate completion, input drift, wrong terminal branch, green/blocked/recovery routes, and artifact receipts.
- Three direct v2 routes: green `completed`, authorization case `blocked`, injected render failure recovered exactly once and `completed`; all artifact integrity gates passed.
- `proofbid eval`: **50/50 passed** in about 22.7 seconds on one local synthetic run. This is not a P95 or production reliability claim.
- `npm run build`: production React build passed.
- Playwright real Chromium at 1440×1000 and 390×844: **4/4 passed**; full workbench screenshots were visually inspected with no observed horizontal overflow or clipping.
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
