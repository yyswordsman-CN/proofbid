# Public HTTPS clean-clone verification — 2026-08-24

> Source: `https://github.com/yyswordsman-CN/proofbid.git`
>
> Verified commit: `dc9d7561b5700e096341d6f78d12c45e25341fb4`

The repository was cloned with `--depth 1` into a fresh directory under
`/tmp`. The repository was public, the clone required no repository
credentials, and the verifier finished with a clean cloned worktree.

## Verified gates

| Gate | Result |
|---|---|
| Python runtime | PASS — Python 3.12.13 |
| Fresh Python environment and dependency installation | PASS |
| Python tests | PASS — 69 passed |
| Synthetic Eval | PASS — 50/50, 0 failed |
| Node runtime | PASS — Node 22.22.3 |
| Frontend production build | PASS |
| Playwright Chromium | PASS — 6/6 desktop/mobile |
| Workbench | PASS — health, POST 202, poll to completed, ZIP download/integrity |
| Docker build | PASS — `proofbid:clean-dc9d7561b570` |
| Docker image | `sha256:d7b5f54752b0b6b86c8c0b537ac95b6c93321fab72a5785e93b7094a65c4d5d6`, `linux/arm64` |
| Non-root container green route | PASS — completed, zero missing, artifact integrity passed |
| Final cloned worktree | PASS — clean |

Workbench task: `task-395ee5db4348478088c9`.

The container route intentionally used `proofbid.scripted-policy`; it verifies
portable packaging and deterministic execution, not real Gemini. Real Vertex
AI Gemini and Cloud Run/GCS evidence is recorded separately in
`docs/evidence/cloud/2026-08-24-verified-closure.md`.

Before publication, the tracked tree contained 127 files and 937,132 bytes;
the largest tracked file was the 202,120-byte architecture PNG. The publication
scan found no tracked populated Google API key, OAuth token prefix, private-key
header, billing-account resource path, Gmail address, or absolute user-home
path. Apache-2.0, third-party notices and pre-existing IP disclosure
are present.

This receipt does not prove Credits approval, video publication, final tag, or
Devpost submission.
