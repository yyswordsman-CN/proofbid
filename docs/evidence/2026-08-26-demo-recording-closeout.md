# Demo recording closeout — 2026-08-26

> Scope: public-safe checkpoint for the ProofBid silent 3:55 demo rehearsal.
> Raw videos, full-resolution contact sheets and local receipts remain under the
> ignored `.proofbid/evidence-raw/rehearsal/` directory.
>
> Historical note: this closeout records the rejected rehearsal stage. It was
> later superseded by the verified edited master and public playback evidence in
> `submissions/google-agentic/demo-clip-ledger.md`.

## Decision

No submission-ready video exists yet. The real Cloud workflows passed, but
neither recording attempt is a complete, publishable final video:

| Take | Cloud truth | Recording result | Decision |
| --- | --- | --- | --- |
| First take | blocked and green executions verified | captured the main desktop instead of the isolated Chrome demo window; unrelated Feishu/WPS content appeared | **Reject; never publish or share** |
| Second take | new green execution verified; prior blocked result shown | privacy isolation passed; the green action appeared around 11–12 seconds and the final GitHub scene was not captured | **Reject as a standalone final video; sanitized segments remain eligible source footage** |

The failure is confined to demo capture and timing. It does not invalidate the
Cloud Run, Gemini, FunctionTool, readiness or artifact evidence.

## Rules-review addendum — 2026-08-26

After the recording closeout, the official Rules, FAQ, submission checklist and
Demo self-check were refreshed. The official guidance asks entrants to show the
product working in the first 10–15 seconds and explicitly allows cutting queue,
loading and other low-information waits. The judging criteria still require
credible live execution.

The original all-in-one 235-second acceptance gate was therefore stricter than
the official submission requirement. This does not convert the second take
into a final video: it still lacks a complete closing scene, English narration
or subtitles, and a submission-ready edit. It does allow its privacy-clean,
reconciled green and blocked segments to be reused in a transparent edit. Every
execution transition must remain bound to its real task/execution ID, receipt,
timestamps and digest. The rejected first take remains prohibited because its
privacy failure cannot be repaired by editing.

## Verified execution checkpoint

### Blocked pre-run

- Task `task-a7fa0092b5e34d3caf1e`
- Cloud Run Job execution `proofbid-agent-k9b8w`
- Terminal state `blocked`; missing items `1`
- Stable reason code `PROJECT_AUTHORIZATION_MISSING`
- Both readiness flags false; `submission_executed=false`; risk actions locked
- Real `google.gemini` / `gemini-3.5-flash` / `STOP`
- Ten FunctionTool call IDs reconciled
- Validated ZIP SHA-256
  `5cdd7bb993f4fe682455f31b3604a55caa1459ab398c857520055e467651f680`

### First-take green

- Task `task-a77f09d578374aba84c5`
- Cloud Run Job execution `proofbid-agent-lhxnc`
- Terminal state `completed`; missing items `0`
- Both readiness flags true; `submission_executed=false`; risk actions locked
- Real `google.gemini` / `gemini-3.5-flash` / `STOP`
- Ten FunctionTool call IDs reconciled
- Validated ZIP SHA-256
  `100f8ccbfb5cec076079320a2fea3f73ddddff085178bdf323ac02aa0ec00773`

### Second-take green

- Task `task-e490d6e1bb4844e1aed4`
- Cloud Run Job execution `proofbid-agent-mccc6`
- Terminal state `completed`; missing items `0`; artifact integrity passed
- Both readiness flags true; `submission_executed=false`; risk actions locked
- Real `google.gemini` / `gemini-3.5-flash` / `STOP`
- Ten FunctionTool call IDs reconciled
- Validated ZIP SHA-256
  `7db4a3c2e713f91678bcea817885da60af3c6e8aa55f4daa6a4fdb32154c3687`

All three executions used revision `proofbid-00003-kdd` and runtime build
`704dbb6d7d7e8114f93bc0dfdf1f18df73267bfd`. The current repository HEAD is a
separate submission/documentation version and must not be described as the
deployed build.

## Recording evidence

### First take — privacy failure

- Raw MOV: 235.001667 seconds, 4096×2304, H.264, 60 fps, no audio
- Raw SHA-256:
  `9bd25ed65e777061767bbaf14eb104baac8dbac0acce3e525fa7562467d75709`
- 1920×1080 MP4 SHA-256:
  `ebb439754fe7b8a242abc301d186cb379873c25220c61589d524803d13dacae1`
- Disposition: local failure evidence only. Do not embed, upload or send.

### Second take — isolated but incomplete

- Raw MOV: 235.018333 seconds, 3680×2392, H.264, no audio
- Raw SHA-256:
  `1560488096df98a2296a36e72a4844a10cc35ca07aec70692630533f6864a9a3`
- Delivery MP4: 235.016667 seconds, 1920×1080, H.264, 60 fps, no audio
- Delivery MP4 SHA-256:
  `0713cb6bf7f887cf0014735959e736de2d2cec1151bbe031e1742f9f0cc91283`
- Window isolation, readability, Cloud proof, green result, Validation,
  Artifacts and blocked result passed visual review.
- Opening 2-second contact sheet shows the green control was still present at
  10 seconds and changed around 11–12 seconds.
- The 230-second final frame remained on the redacted blocked receipt rather
  than the public GitHub repository.

## Design checkpoint

- **User and job:** a hackathon judge must understand one bounded professional
  task, verify the Google agent/cloud path and distinguish safe completion from
  truthful blocking in under four minutes.
- **Information priority:** real task start → architecture/runtime proof → live
  completed delivery → truthful blocked delivery → reproducibility.
- **Visual character:** precise, evidence-led, restrained.
- **Signature move:** the tool-call timeline and deterministic readiness panel
  turn agent autonomy into inspectable evidence rather than an avatar or chat
  transcript.
- **Restraint rule:** no fake dashboards, invented metrics, decorative agent
  personas, misleading edits or status claims unsupported by receipts.

The Workbench remains a strong **Executive evidence + Precision product**
direction. Its best design decision is semantic separation between
`ready_for_submission=true` and `submission_executed=false`; the UI makes
bounded autonomy visible without implying that ProofBid submitted a bid.

## Pitfalls and corrected operating rules

The timing, final-frame and frame-rate rules below describe the original
one-take rehearsal workflow. They remain useful when capturing new continuous
source footage, but they are no longer independent official eligibility gates
for the edited final video.

### 1. Display capture is not window capture

The first take used main-display recording. Chrome lived in a different window
coordinate space, so app-level automation could change Chrome while the video
captured another desktop. App screenshots and accessibility state were not
proof of what `screencapture -D1` recorded.

**Rule:** resolve the exact Chrome window ID and record with window binding.
Before a paid/full run, record a ten-second window-bound probe, extract a middle
frame and visually approve it.

### 2. Recorder startup latency consumes the opening budget

Starting the native recorder, returning control to the automation layer and
then clicking sequentially pushed the green click just beyond ten seconds.
Cloud `accepted` time is later still and is not a substitute for the visible
click timestamp.

**Rule:** start capture and schedule the green click concurrently. Target the
visible click by 0:03–0:05, then validate it from a 0–12 second contact sheet at
two-second intervals.

### 3. Automation state is not captured-frame evidence

The browser accessibility state reported the GitHub tab at the end, while the
recorded window remained on the receipt. A successful keyboard command and a
correct browser state query did not prove the recorder had the intended final
frame.

**Rule:** use a direct tab element click for the final repository scene no
later than 3:30, keep it unchanged through 3:55, and inspect an extracted
230-second frame before accepting the take.

### 4. Browser chrome is part of the privacy surface

Window capture fixed cross-app leakage, but the address bar, local file path,
tab titles and profile chrome remain visible.

**Rule:** hide the bookmarks bar; keep only approved public/redacted tabs;
prefer served redacted receipts over local filesystem pages when practical;
inspect the tab strip, address bar, avatar and notifications at full resolution.

### 5. Native capture frame rate needs normalization

The window-bound MOV advertised a 120 fps time base while effective capture was
lower. A first transcode inherited 120 fps unnecessarily.

**Rule:** record the actual delivery resolution, frame rate and audio layout;
preserve aspect ratio and readability. Use a stable final encode, but do not
present 60 fps or a silent audio layout as an official requirement.

### 6. Failed takes still need evidence discipline

The first take contained private/unrelated material. Keeping it in an ignored
directory preserved the audit trail without turning it into a public artifact.

**Rule:** raw media stays under `.proofbid/evidence-raw/`; publish only a
sanitized Markdown conclusion and hashes. Never attach or preview the rejected
first take.

## Practices worth keeping

- Reuse the independently reconciled green and blocked source footage when it
  remains readable; create a new Cloud task only with explicit authorization
  and only when the existing source cannot support a truthful final edit.
- Cut Cloud provisioning and loading waits transparently while preserving the
  same task/execution identity and keeping at least one continuous real action
  segment.
- Bind every visible claim to real Gemini, FunctionTool call IDs, terminal
  state, readiness fields, artifact integrity and digest/hash reconciliation.
- Keep green and blocked cases structurally identical except for the single
  missing authorization, making the safety contrast credible and legible.
- Show `submission_executed=false` and locked high-risk actions in both paths.
- Review a normal contact sheet, an opening high-frequency contact sheet and a
  final-frame extraction; each answers a different acceptance question.
- Treat recording, validation, publication and Devpost submission as separate
  states with separate authorization and receipts.

## Quality-gate result

- Truthful content: PASS
- Primary Workbench task: PASS based on real green and blocked routes
- System and semantic integrity: PASS; no product code or component system was
  changed during recording
- Render verification: PASS for the captured desktop route and states
- Demo artifact acceptance: **BLOCKED as a standalone final video**; the
  privacy-clean second take is approved only as source footage for a new edit

No visual quality score is assigned because this closeout made no interface
change. A score would imply a new design evaluation that was not performed.

## Exact resume condition

Do not create another Cloud task automatically.

1. Inventory the privacy-clean second-take source and map usable time ranges to
   the verified green and blocked task/execution IDs.
2. Record only local-safe missing material: architecture, repository and clear
   English narration or subtitles.
3. Assemble a 3:30–3:50 transparent edit using
   `submissions/google-agentic/demo-script.md`; preserve a continuous real
   click-to-accepted opening segment and document all execution cuts.
4. Reconcile the final clip ledger against Cloud receipts, timestamps,
   revision/image digest and artifact hashes; perform full privacy, readability,
   audio/caption and duration review.
5. If source footage is insufficient, stop and request authorization for
   exactly one new green execution rather than silently creating it.
6. Only a fully passing edit may proceed to publication, freeze tag or Devpost,
   each under its own explicit authorization.
