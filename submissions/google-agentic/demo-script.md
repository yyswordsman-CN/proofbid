# Four-minute demo script

> Target length: 3:55. English narration or verified English subtitles. The green and blocked executions must be real Cloud Run Job runs, not prerecorded UI mocks.

## 0:00–0:25 — Problem and value

“Tender preparation is not a chat question. It is a multi-step professional task where every claim needs evidence, every number must agree across files, and one missing authorization can invalidate the package. ProofBid takes one event and autonomously delivers a reviewable tender-preparation bundle.”

## 0:25–0:45 — Architecture

Show `docs/architecture/proofbid-google-cloud-1920x1080.png` full-screen.

“The React event reaches a Cloud Run service, which returns 202 and starts a Cloud Run Job. Gemini 3.5 Flash routes Google ADK FunctionTools. Deterministic code owns facts, BOM, rendering, and release. Cloud Storage keeps state, receipts, Trace, and the final ZIP.”

## 0:45–2:05 — Green case

Click `Complete tender package` once. Show queued/running, the Cloud execution ID, then the complete timeline.

“No follow-up prompt is needed. The agent scans the immutable input manifest, chooses tools, builds the evidence-bound analysis, renders the package, runs both validation layers, and selects `finalize_complete` only after readiness is true.”

Open Evidence, Validation, and Artifacts. Download the ZIP. Show `ready_for_human_review=true`, `ready_for_submission=true`, `submission_executed=false`, and locked high-risk actions.

## 2:05–3:05 — Blocked case

Click `Authorization missing` once.

“The same autonomous workflow reaches a different business terminal state. Project authorization is absent. ProofBid does not infer it from the product catalog and does not fabricate it. The agent selects `finalize_blocked`, then delivers a validated evidence ledger and missing-item package.”

Show `Missing items = 1`, `PROJECT_AUTHORIZATION_MISSING`, both readiness flags `false`, and the still-downloadable validated ZIP.

## 3:05–3:35 — Agent and cloud proof

Show the redacted `proofbid-cloud-evidence` summary, `agent_run.json`, `tool_receipts.jsonl`, the Cloud Run Job execution, and matching Cloud Logging/GCS timestamps and hashes.

“The receipt records the observed Gemini model version, usage, finish reason, invocation ID, tool choices, retry relationship, and digest chain—without secrets, prompts, or hidden reasoning.”

If time permits, point to one recorded recovery run where `render_delivery` returns `RENDER_TRANSIENT` and Gemini chooses `retry_render` exactly once.

## 3:35–3:55 — Reproducibility

Show the public repository, Apache-2.0 license, quick start, test result, 50-case Eval result, commit/tag, and Cloud revision digest.

“ProofBid completes the safe professional task, explains truthful blockers, and keeps signing and submission under human control.”
