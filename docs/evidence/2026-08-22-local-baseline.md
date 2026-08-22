# ProofBid local Git baseline evidence

> Captured: 2026-08-22 15:16 CST
> Source commit: `699a6f53d2ea5a0a900a00a60bcbfb9dd7cbede6`
> Scope: local source, synthetic fixtures, test/build output and local Docker only

## Verified results

| Gate | Result | Evidence |
|---|---|---|
| Python suite | PASS | 55 passed, 0 failed, 3 upstream warnings; 7.89 s wall time |
| Synthetic Eval | PASS | 50/50; suite duration 27,300.36 ms; no P95 or production claim |
| React production build | PASS | Vite 8.2.2; generated HTML/CSS/JS hashes retained in the JSON receipt |
| Playwright | PASS | 4/4 at 1440×1000 and 390×844 after starting the documented FastAPI service |
| Docker build | PASS | `sha256:3d7e7ebc3545...`, `linux/arm64`, non-root user `65532:65532` |
| Container green route | PASS | `completed`, zero missing items, artifact integrity passed |

The first Playwright attempt was blocked by the macOS sandbox. The next attempt launched Chromium but correctly failed because no server was running. The final evidence run started `uvicorn proofbid.service:app` on `127.0.0.1:8080` and passed all four assertions. Only the final run is treated as the product result; the earlier failures are retained here as environment evidence.

## Known gaps frozen by this baseline

1. `blocked_missing_authorization` produces six blocking missing items, not one. Its bundle SHA-256 is `0b4e1a020a359039ecc2518e91640a6117ed92bf17341d99845ebd011ab5d50d`.
2. The v2 Google tool-agent path initializes `planner_receipt.json` with `proofbid.scripted-policy`; no real Gemini network call or Vertex usage receipt has been captured.
3. No `gcloud`, Billing Account, Cloud Run, GCS, public repository, Devpost join, Credits receipt, video or submission evidence exists at this point.

These gaps are failures-to-complete, not hidden exceptions. Later commits must preserve this baseline and add separate evidence for each closure.
