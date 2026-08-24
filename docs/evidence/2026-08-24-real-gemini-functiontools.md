# Real Gemini FunctionTool evidence

> Captured: 2026-08-24 21:57 CST
> Source commit: `7f183aa3c8af50f656201d96c4f19d17761a155b`
> Google Cloud project: `proofbid-agentic-yys-260822`
> Scope: local ProofBid execution using Vertex AI ADC and synthetic public fixtures

## Gate outcome

PASS. Both the complete and single-authorization-missing fixtures used the real
`google.gemini` provider through Vertex AI ADC with configured and observed model
`gemini-3.5-flash`. Both runs reported `STOP`, non-zero usage, a provider
invocation ID, and ten unique non-null ADK FunctionTool call IDs. Recursive
scripted-fallback scans returned no marker.

| Case | Terminal state | Readiness | Missing items | FunctionTools | Tokens | Duration |
|---|---|---|---:|---:|---:|---:|
| `complete_tender` | `completed` / `finalize_complete` | review `true`; submission `true` | 0 | 10/10 IDs | 1,650 | 17,942.144 ms |
| `blocked_missing_authorization` | `blocked` / `finalize_blocked` | review `false`; submission `false` | 1 | 10/10 IDs | 1,740 | 18,522.967 ms |

The blocked case retained `PROJECT_AUTHORIZATION_MISSING`, kept high-risk
actions locked, and still delivered an integrity-validated ZIP. It differs from
the green fixture only by the project-specific manufacturer authorization
evidence. `MANDATORY_REQUIREMENT_RESOLVED` is the existing deterministic
validator classification attached to an unresolved mandatory requirement; the
missing-item business code remains `PROJECT_AUTHORIZATION_MISSING`.

## Provider receipts

### Green

- Task: `task-661ce92c9534473a95ac`
- Invocation: `e-91bcaa2f-b504-4376-91cf-5774bb0fb82f`
- Provider: `google.gemini`; auth: `vertex_ai`
- SDKs: Google ADK `2.7.1`; google-genai `2.18.1`
- Usage: 1,613 prompt + 20 output = 1,650 total tokens
- Events: 21; finish reason: `STOP`
- ZIP SHA-256: `57818bfcbcbb18e863c22c9f9e2e573a2ea7a2076ba158ad117dff325614e1ef`
- Manifest SHA-256: `bfa96be0455ac243e96a234cb1c5daa61cdb5877481c4ac36f502af29384733b`
- `agent_run.json` SHA-256: `d2fcac2a54109405b5d23b4be332aad7a001da3ba36c1048d903a05c6c929af8`
- `tool_receipts.jsonl` SHA-256: `fde8c77de65dcfb65a169fc98963cd1ea4d00579c2a54a1fde3aa44cbe879536`

### Blocked

- Task: `task-936c05fd3d1e40eb8830`
- Invocation: `e-9c59549c-2de1-4486-bf76-7144a35879aa`
- Provider: `google.gemini`; auth: `vertex_ai`
- SDKs: Google ADK `2.7.1`; google-genai `2.18.1`
- Usage: 1,693 prompt + 19 output = 1,740 total tokens
- Events: 21; finish reason: `STOP`
- ZIP SHA-256: `eba79212d569c1a9e40dbdab16260473b52883cc533142ecd5b8d7a9760f6dde`
- Manifest SHA-256: `b2c6a5ceddac1632ed31c958cd755aaedc58eeba904911da29d99412e200d7c8`
- `agent_run.json` SHA-256: `ff42fcfe60e1de27fc27a73ffd200f38a0a9f549938ee00cdee4883bab1eb378`
- `tool_receipts.jsonl` SHA-256: `5594e5fd4cb53af21633dced75dfdcd1ce81b158b17ce945d9d598da50c8a6fd`

## Failure retained before success

The first authenticated attempt did not reach Gemini. Prompt construction
called a nonexistent `TaskInputRef.to_dict()` method and failed locally. Commit
`7f183aa` now serializes inputs through the versioned `TaskSpec.to_dict()`
contract and adds a regression test. The full suite passed with 68 tests before
the commit-bound evidence runs above.

## Evidence boundary

This proves real local Gemini + ADK FunctionTool execution. It does not prove a
Cloud Run deployment, Cloud Run Job execution, GCS generation, Cloud Logging
event, public repository, Credits approval, video, or Devpost submission.
Complete raw deliveries are retained locally under the ignored
`.proofbid/evidence-raw/real-gemini/` directory.
