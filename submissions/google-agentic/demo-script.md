# Four-minute demo script

> Target length: 3:55. English narration or verified English subtitles. The green and blocked executions must be real Cloud Run Job runs, not UI mocks. The measured public-browser probe took about 2:25 for green and 2:58 for blocked, so only green runs during recording; blocked is executed immediately beforehand and kept open in a separate tab.

## Before recording — prepare without faking

- Run `Authorization missing` once in the public Workbench and keep the completed tab open at `Missing items = 1`.
- Pre-open the architecture PNG, Cloud Run Job execution list, redacted evidence receipt, public repository, and a previously verified extracted green ZIP as a navigation backup.
- Return to a fresh public Workbench home. Do not start the green route until recording begins.

## 0:00–0:10 — Start the real green event

Click `Complete tender package` once. Keep the accepted task and Cloud execution ID visible.

“One public-safe tender event starts a real Cloud Run Job. While it provisions, here is why the task and its controls matter.”

## 0:10–0:35 — Problem and value

“Tender preparation is not a chat question. It is a multi-step professional task where every claim needs evidence, every number must agree across files, and one missing authorization can invalidate the package. ProofBid takes one event and autonomously delivers a reviewable tender-preparation bundle.”

## 0:35–1:05 — Architecture

Show `docs/architecture/proofbid-google-cloud-1920x1080.png` full-screen.

“The React event reaches a Cloud Run service, which returns 202 and starts a Cloud Run Job. Gemini 3.5 Flash routes Google ADK FunctionTools. Deterministic code owns facts, BOM, rendering, and release. Cloud Storage keeps state, receipts, Trace, and the final ZIP.”

## 1:05–2:15 — Backend and bounded autonomy while green runs

Show the current execution in Cloud Run, then the source-bound revision/image digest and a recorded redacted FunctionTool receipt from the same pinned runtime revision.

“Gemini chooses the bounded tool order and legal terminal branch. It cannot provide paths, facts, prices, shell, SQL, URLs, or submission actions. Deterministic tools own evidence, calculation, rendering, and release.”

Return to the green Workbench around 2:15. If it remains queued, use the remaining narration buffer without hiding the wait.

## 2:15–2:55 — Green completion

Show the complete timeline when the live route reaches `completed`.

“No follow-up prompt is needed. The agent scans the immutable input manifest, chooses tools, builds the evidence-bound analysis, renders the package, runs both validation layers, and selects `finalize_complete` only after readiness is true.”

Open Validation and Artifacts. Trigger the ZIP download. Show `ready_for_human_review=true`, `ready_for_submission=true`, `submission_executed=false`, and locked high-risk actions.

## 2:55–3:20 — Real blocked result

Switch to the real blocked Workbench tab completed immediately before recording.

“The same autonomous workflow reaches a different business terminal state. Project authorization is absent. ProofBid does not infer it from the product catalog and does not fabricate it. The agent selects `finalize_blocked`, then delivers a validated evidence ledger and missing-item package.”

Show `Missing items = 1`, `PROJECT_AUTHORIZATION_MISSING`, both readiness flags `false`, and the still-downloadable validated ZIP.

## 3:20–3:42 — Agent and cloud proof

Show the redacted `proofbid-cloud-evidence` summary, `agent_run.json`, `tool_receipts.jsonl`, the Cloud Run Job execution, and matching Cloud Logging/GCS timestamps and hashes.

“The receipt records the observed Gemini model version, usage, finish reason, invocation ID, tool choices, retry relationship, and digest chain—without secrets, prompts, or hidden reasoning.”

Do not add a live recovery run. If time permits, point to the recorded recovery receipt where `render_delivery` returns `RENDER_TRANSIENT` and Gemini chooses `retry_render` exactly once.

## 3:42–3:55 — Reproducibility

Show the public repository, Apache-2.0 license, quick start, test result, 50-case Eval result, commit/tag, and Cloud revision digest.

“ProofBid completes the safe professional task, explains truthful blockers, and keeps signing and submission under human control.”
