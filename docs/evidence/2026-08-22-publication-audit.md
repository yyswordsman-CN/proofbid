# Public repository preflight — 2026-08-22

Audited commit: `c98c2c9f8d8859933400313e53e87124211934f6`.

## Passed local checks

- Worktree was clean before the audit.
- 108 tracked files, 867,350 total tracked bytes; largest tracked file was the 202,120-byte architecture PNG. No tracked file exceeded 2 MiB.
- No tracked Google API key pattern, OAuth token prefix, private-key header, or `/Users/yangzhiyi` absolute path was found.
- `.env`, build output, Node dependencies, and raw cloud-evidence downloads are ignored.
- No public UI/API control exposes `PROOFBID_INJECT_RENDER_FAILURE`.
- Apache-2.0 `LICENSE`, `PREEXISTING_IP.md`, and `THIRD_PARTY_NOTICES.md` are present.

Disclosure hashes:

- `LICENSE`: `03e999c6a504a0838963a6eaaf6c7aafad93b6dd5823f5f50da558310ed18a2c`
- `PREEXISTING_IP.md`: `a2f36c9e711f21109bec6c29ed0dceed8b7679aaabb474435456c235a57f19bd`
- `THIRD_PARTY_NOTICES.md`: `f1c1584938dc20055fbc3cb1739b8b150a2686e4763b0daa38fc72803fb5a3b8`

## Publication blocker

`gh auth status` reports that the active `yyswordsman-CN` token is invalid. A device-login attempt was opened but expired before owner authorization. No GitHub remote, public repository, push, or tag exists. Therefore this receipt is a local publication preflight, not evidence that the repository is public.
