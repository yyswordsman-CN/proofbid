# Local clean-clone evidence — 2026-08-22

The second clean-clone run passed from commit `97da57903ade4a9bb47ada42c0ff52f7a6bff0e8` with Python 3.12.13 and Node 22.22.3.

## Verified

- Fresh Python/Node dependency installation completed.
- Python: 67 passed, 0 failed.
- Synthetic Eval: 50/50 passed in 20.851 seconds.
- React production build passed; Playwright desktop/mobile: 6/6 passed.
- Local Workbench health, POST 202, polling to `completed`, ZIP download, and ZIP integrity passed for task `task-4dd6d4ff9ff54763bd15`.
- Docker image `proofbid:clean-97da57903ade` built as `sha256:3f8efd347274c6ec3f423bce132f59c58fb5b067fc07386cb6151bf11cb49be3` for `linux/arm64`; its non-root green task completed with artifact integrity passed.
- The cloned worktree remained clean after verification.
- Mermaid CLI 11.16.0 produced the reviewed SVG and exact 1920×1080 PNG; hashes are recorded in the JSON receipt.

## Failure found and fixed

The first clean-clone attempt at `3419bba` passed tests but failed the installed `proofbid eval` command because it resolved `examples/` under the virtual environment. Commit `97da579` added checkout/container-aware asset-root resolution and two regression tests; the full clean-clone run then passed.

## Remaining boundary

This was a clone from the local Git repository. It does not satisfy the final public HTTPS clone gate because GitHub authentication and the public repository are not yet available. It also does not prove Gemini or Google Cloud execution; the Docker route intentionally used the local scripted policy.
