# Video rehearsal timing probe — 2026-08-25

> This is a live technical timing probe of the public Workbench and two real
> Cloud Run Job routes. It is not yet a recorded or published 3:55 video.

## Public-browser route

- Public Workbench: `https://proofbid-um2t63h7ha-uc.a.run.app`
- Browser access required no privileged credentials.
- Both public fixture buttons were visible; arbitrary upload and submission
  actions were absent.

## Measured executions

| Route | Task | Execution | Browser click to observed terminal | Cloud accepted to delivery-ready | Provider | Result |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Green | `task-f2684b5a3cc449e0af90` | `proofbid-agent-snpnp` | 145.1 s | 134.8 s | 13.2 s | completed; missing 0; 10 FunctionTools |
| Single authorization missing | `task-e19d99b5570d44928136` | `proofbid-agent-htj58` | 178.0 s | 161.7 s | 13.1 s | blocked; missing 1; `PROJECT_AUTHORIZATION_MISSING` |

The majority of elapsed time was Cloud Run Job provisioning/queueing rather
than Gemini execution. Both runs used revision `proofbid-00003-kdd`, the
digest-pinned image built from `704dbb6`, real `gemini-3.5-flash`, non-zero
usage and ten unique FunctionTool call IDs.

The green ZIP was downloaded again from the public Service. `unzip -t` passed
for all twelve delivered files and its SHA-256
`69b5fccd6111f62ccb53548f86a4d8977da686564ce0439f753345c67b331d49`
matched the GCS, manifest and evidence-collector receipt.

Machine-readable reconciliation:

- `docs/evidence/cloud/task-f2684b5a3cc449e0af90.json`
- `docs/evidence/cloud/task-e19d99b5570d44928136.json`

## Recording decision

Two live executions cannot reliably fit inside 3:55. For the uncut recording:

1. Run the blocked route immediately before recording and keep its completed
   Workbench tab open.
2. Start recording on the public Workbench and click the green route within the
   first ten seconds.
3. Use the green provisioning interval to present the problem, architecture and
   Cloud Run backend proof.
4. Return to the green tab around 2:15, using a short narration buffer if it is
   still queued.
5. Show green readiness, validation and artifacts, then switch to the pre-run
   real blocked tab and show `missing_items=1` plus the stable reason code.
6. Finish with the provider/FunctionTool/hash receipt and frozen public source.

The blocked tab is a real Cloud Run/Gemini result, not a mock or prerecorded UI.
At least the complete green event-to-delivery execution remains visible within
one uncut recording.
