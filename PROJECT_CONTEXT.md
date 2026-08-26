# PROJECT_CONTEXT — ProofBid

> Last updated: 2026-08-26

## Current implementation

- The independent Git repository preserves the original baseline commits (`699a6f5` and `7a4c744`), is public at `https://github.com/yyswordsman-CN/proofbid`, and has a clean verified public baseline. The local frozen submission snapshot is identified by annotated tag `google-agentic-2026-submission`; the freeze commit and tag are not yet pushed.
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
- The All Things Agentic Hackathon USD 150 promotional Credits were approved and redeemed on 2026-08-25. The Billing UI shows the localized promotional balance available through 2026-09-24 and the separate Free Trial balance through 2026-11-23; a read-only CLI check reconfirmed `billingEnabled=True`. See `docs/evidence/2026-08-25-google-cloud-credits.md`.
- Commit `7f183aa` passed real local `gemini-3.5-flash` + ADK FunctionTool execution for both public fixtures. Green reached `completed` with 1,650 tokens; blocked reached `blocked` with one `PROJECT_AUTHORIZATION_MISSING` item and 1,740 tokens. Both reported `google.gemini`, Vertex AI ADC, `STOP`, real invocation IDs, 10/10 unique non-null FunctionTool call IDs, no scripted marker, locked high-risk actions, and integrity-validated ZIPs. See `docs/evidence/2026-08-24-real-gemini-functiontools.md`.
- Commit `704dbb6` is deployed with digest `sha256:17bbebcf2c3511b187279ee20cea9ec6359a6a6e763f66cfc0bbc056ce5c8aca`. Three green, three single-authorization blocked and one administrator-only renderer-recovery Cloud Run Job executions completed and independently reconciled across real Gemini/FunctionTool receipts, terminal state, Service/GCS ZIP hashes, revision/image digest and structured logs. The blocked runs each contain one `PROJECT_AUTHORIZATION_MISSING` item and both readiness flags false. The recovery run records `RENDER_TRANSIENT`, exactly one `retry_render`, and final completion. See `docs/evidence/cloud/2026-08-24-verified-closure.md`.
- Three direct v2 routes: green `completed`, authorization case `blocked`, injected render failure recovered exactly once and `completed`; all artifact integrity gates passed.
- `proofbid eval`: **50/50 passed** in about 22.7 seconds on one local synthetic run. This is not a P95 or production reliability claim.
- `npm run build`: production React build passed.
- Playwright real Chromium at 1440×1000 and 390×844: **6/6 passed** after the single-authorization UI change, including visible missing count, stable reason code and blocked ZIP download.
- Fresh green and blocked Word/Excel files were reopened with LibreOffice and exported to PDF. Both Word reports rendered as two landscape pages; the green/blocked first pages and workbook summaries were visually inspected. The green report wording was corrected to reflect evidenced quote inclusions, and workbook print settings reduced horizontal pagination.
- `bash -n infra/cloud-shell-deploy.sh`: passed.
- `docker build -t proofbid:local .`: multi-stage image built successfully after transient registry retries.
- The non-root built image ran the complete tender through Agent v2 and returned `completed`, both readiness flags `true`, 10 tool calls, and artifact integrity passed.
- A fresh public HTTPS clone of `https://github.com/yyswordsman-CN/proofbid.git` at commit `dc9d756` passed Python 3.12.13 dependency installation, 69 tests, 50/50 Eval, Node 22.22.3 install/build, 6/6 Playwright, Workbench health/202/poll/download, Docker build, ZIP integrity, a non-root container green route, and the final clean-worktree gate. See `docs/evidence/2026-08-24-public-clean-clone.md`.
- A clean public-browser video timing probe ran one new green and one new single-authorization blocked Cloud Run Job. Browser click-to-terminal observations were about 145 seconds and 178 seconds respectively; both independently reconciled real Gemini/FunctionTool, logs, revision/image digest and Service/GCS ZIP hashes. The green ZIP was downloaded again and passed `unzip -t`. See `docs/evidence/2026-08-25-video-rehearsal-timing.md`.
- Repository scan found no populated API keys/private keys, user name, or absolute local project path.

## Checkpoint — 2026-08-25 closeout

### Repository and runtime binding

- Public `main` and local `main` were aligned at `a426106` before this
  checkpoint edit. The two commits produced in the session were `f3dc2d4`
  (`docs: record approved Google Cloud credits`) and `a426106`
  (`docs: record cloud video rehearsal timing`).
- The deployed runtime remains intentionally bound to source commit `704dbb6`,
  revision `proofbid-00003-kdd`, and image digest
  `sha256:17bbebcf2c3511b187279ee20cea9ec6359a6a6e763f66cfc0bbc056ce5c8aca`.
  Later public commits are evidence and submission-document updates; do not
  present the submission HEAD as the deployed build version.

### Reference cases worth reusing

- **Green video probe:** `task-f2684b5a3cc449e0af90` /
  `proofbid-agent-snpnp`; browser click-to-terminal 145.1 s, cloud
  accepted-to-delivery 134.8 s, provider 13.2 s, 1,746 total tokens, ten
  FunctionTools, 12/12 requirements, 63 evidence refs, missing 0, completed.
  Its public Service ZIP passed `unzip -t` and matched the GCS/manifest hash
  `69b5fccd6111f62ccb53548f86a4d8977da686564ce0439f753345c67b331d49`.
- **Single-variable blocked probe:** `task-e19d99b5570d44928136` /
  `proofbid-agent-htj58`; browser click-to-terminal 178.0 s, cloud
  accepted-to-delivery 161.7 s, provider 13.1 s, 1,777 total tokens, ten
  FunctionTools, missing 1, both readiness flags false, stable code
  `PROJECT_AUTHORIZATION_MISSING`, validated ZIP delivered.
- **Bounded recovery reference:** `task-61cf08577c9b1605d41e` /
  `proofbid-agent-fd79q`; one `RENDER_TRANSIENT`, exactly one
  `retry_render`, then completed. Keep this as receipt evidence; never expose
  recovery as a public button or add another live execution to the four-minute
  demo.

### Pitfalls and operating lessons

- Cloud Run Job provisioning dominated both probes: roughly two minutes were
  queue/provisioning while Gemini itself took about 13 seconds. Two live routes
  cannot reliably fit inside 3:55. Start one live green task at 0:00 and use its
  queue interval for the problem, architecture and Cloud proof; pre-run the
  real blocked route immediately before recording.
- Workbench task results are SPA state at the same `/` URL, not durable deep
  links. A pre-run blocked tab must remain open and must not be reloaded. GCS
  task objects also have a seven-day lifecycle, so do not depend on old August
  24 tabs or task IDs for the final recording.
- The in-app browser did not emit a reliable download event for the ZIP link;
  this did not mean the Service download failed. The public bundle endpoint was
  independently checked with `curl`, `unzip -t`, SHA-256 and GCS reconciliation.
  For recording, keep a previously verified extracted ZIP open as navigation
  backup while still clicking the live task's download link on screen.
- `gcloud` needs its normal user configuration directory. A restricted sandbox
  can fail with permissions on `~/.config/gcloud` even when authentication is
  valid; rerun approved read-only cloud checks with the normal user context
  rather than treating that error as an auth or Billing failure.
- The approval email described three months of promotional-credit use, but the
  authoritative Billing Credits page shows the hackathon credit ending
  2026-09-24. Use the console date as the hard operational deadline. The
  expired one-day Free Trial row is an account-upgrade transition record, not a
  second USD 300 grant.
- Credits screenshots and email contain a one-time code/account context. Raw
  files belong only in ignored `.proofbid/evidence-raw/`; public evidence keeps
  redacted facts and hashes. Never commit the promotion code, Billing Account
  resource path, email address or raw Billing screenshots.

### Resume sequence

This sequence was superseded by the 2026-08-26 official Rules/FAQ/submission
guidance refresh and the edited-video decision below. Do not use the old
all-in-one one-take gate as the current NEXT.

## Checkpoint — 2026-08-26 demo recording closeout

- Two continuous 235-second silent takes were recorded and reviewed. Neither
  is submission-ready; see
  `docs/evidence/2026-08-26-demo-recording-closeout.md`.
- The first take captured the main desktop instead of the isolated Chrome demo
  window and exposed unrelated Feishu/WPS content. Its MOV, MP4 and unredacted
  contact sheet remain ignored local failure evidence and must never be shared
  or published.
- The second take bound recording to the exact Chrome window, removed the
  cross-app privacy failure and clearly showed the public Workbench,
  architecture, Cloud Run, redacted receipt, completed green timeline,
  Validation, Artifacts and the real blocked result. It is not a complete final
  video because it lacks the closing repository scene, English narration or
  subtitles, and a reviewed submission edit. Its action appears around 11–12
  seconds, which is inside the official 10–15 second recommendation.
- The blocked pre-run `task-a7fa0092b5e34d3caf1e` /
  `proofbid-agent-k9b8w`, first-take green
  `task-a77f09d578374aba84c5` / `proofbid-agent-lhxnc`, and second-take green
  `task-e490d6e1bb4844e1aed4` / `proofbid-agent-mccc6` were independently
  reconciled. Each used real `gemini-3.5-flash`, ten FunctionTools and the
  pinned runtime `proofbid-00003-kdd` / `704dbb6`; both green tasks completed,
  while the blocked task retained exactly one
  `PROJECT_AUTHORIZATION_MISSING` item and false readiness.
- Proven recorder rule: a Chrome accessibility screenshot is not proof of the
  captured display. Bind source capture to the exact window ID and visually
  inspect the resulting media; automation state alone is not frame evidence.
- The Workbench design direction remains **Executive evidence + Precision
  product**: tool timeline, deterministic readiness, locked high-risk actions
  and digest-bound receipts carry the story. Avoid avatars, fake dashboards,
  decorative Agent chrome, misleading edits or unverified performance/cost
  claims.
- The 2026-08-26 official refresh confirmed that transparent cuts may remove
  Cloud queue/loading time while one real action segment and end-to-end task,
  execution and digest continuity remain verifiable. The privacy-clean second
  take is therefore eligible source footage, but not a submission-ready video.
- No product code, API, Schema, deployment, new Cloud execution, commit, push,
  tag, publication or Devpost submission was performed during the documentation
  and recording closeout.

## Checkpoint — 2026-08-26 edited Demo master

- The privacy-clean second take was converted to a 1920×1080 upload derivative
  and assembled in ChatCut with nine evidence-bound visual scenes, nine Peter /
  ElevenLabs English narration segments and one original restrained instrumental
  BGM bed. No new Cloud execution was created.
- The final local candidate is
  `ProofBid-Google-Agentic-Demo-final-v2.mp4`: 211.221 seconds container /
  211.167 seconds video, 1920×1080, 30 fps, 6,335 H.264 frames with AAC-LC
  48 kHz stereo audio. SHA-256 is
  `c34c53df0cc3fa5ad1acb7c0e31b8d5f01c3d89e4a499edb448d87a033d3478f`.
- Full decode passed. Audio measured `-13.33 LUFS` integrated with `-2.08 dBTP`
  true peak. Local Whisper large-v3-turbo independently re-transcribed the
  narration; the blocked sentence was separately confirmed as “does not infer
  or fabricate it.”
- Sixteen final-render chapter/boundary frames passed visual review. A 0.33-second
  blank Cloud-entry frame found in v1 was removed by shifting that source in-point
  to 90.050 seconds. The receipt scene is zoomed and cropped so the private local
  path is absent while task, execution, model, reason code, revision and hash
  evidence remain visible.
- `submissions/google-agentic/demo-clip-ledger.md` now records the final ranges,
  task/execution bindings, narration/audio review, privacy review and export hash.
- The exact verified MP4 was published publicly on YouTube on 2026-08-26 at
  `https://youtu.be/E4Ke_cWLFus`. YouTube completed processing and reported
  “未发现任何问题” for the copyright check before publication. The upload was
  marked as English, not made for children, and disclosed as AI-generated or
  edited content.
- Anonymous verification passed after publication. A no-cookie watch-page
  request returned `playabilityStatus=OK`, `streamingData`, video ID
  `E4Ke_cWLFus` and a 211-second duration. A separate privacy-enhanced
  `youtube-nocookie.com` player reached `readyState=4`, decoded 640×360 video,
  reported a 211.241-second duration and advanced continuously while unpaused.
- Publication itself did not create a Git commit/tag, push later changes or
  submit Devpost. The subsequent local freeze is identified by annotated tag
  `google-agentic-2026-submission`; pushing the frozen refs and submitting
  Devpost remain unperformed and separately controlled.

## Evidence not yet obtained

- Seven verified cloud observations provide token and provider-duration samples, but no production P95 or attributed Google Cloud cost claim has been made.
- The public repository exists at `https://github.com/yyswordsman-CN/proofbid`;
  `main` is pushed and public HTTPS clean-clone verification passed. The final
  video is publicly available at `https://youtu.be/E4Ke_cWLFus` and anonymous
  playback verification passed. The local freeze commit/tag exists, but its
  refs have not been pushed; no Devpost submission, source-archive receipt or
  final submission receipt exists yet.

## Locked scope

- Main category: The Taskmaster; additional targets are Individual/Hobbyist and Best Architectural Design.
- Public demo: English, synthetic, only two built-in fixtures, Apache-2.0.
- Infrastructure: Cloud Run Service + Cloud Run Job + Cloud Storage + Vertex AI ADC. No Firestore, Pub/Sub, multi-agent system, PDF/OCR, signing, sending, pricing freeze, or submission.
- Real cloud resource creation, public push, video publication, and Devpost submission require explicit user authorization.

## Unique NEXT

The real-provider matrix, Cloud evidence, Credits, public HTTPS clean clone,
browser timing probe, verified English Demo master, public YouTube publication,
anonymous playback check and local freeze commit/tag are complete. The unique
NEXT is to obtain explicit authorization to push the frozen commit and annotated
tag, then anonymously verify both remote refs. Do not create another Cloud task,
deploy, move the tag or submit Devpost; final Devpost submission must preserve
its own action-time confirmation, source archive hash and receipt.
