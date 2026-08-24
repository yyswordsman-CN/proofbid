# ProofBid verified Google Cloud closure — 2026-08-24

> Scope: three independent green runs, three independent single-authorization
> blocked runs, and one administrator-only renderer recovery run. All inputs are
> public-safe synthetic fixtures. Credits approval, public repository, video,
> tag, and Devpost submission are outside this receipt.

## Shared deployment binding

- Google Cloud project: `proofbid-agentic-yys-260822`
- Source/build commit: `704dbb6d7d7e8114f93bc0dfdf1f18df73267bfd`
- Image digest: `sha256:17bbebcf2c3511b187279ee20cea9ec6359a6a6e763f66cfc0bbc056ce5c8aca`
- Green-only revision: `proofbid-00002-jq7`
- Two-fixture revision: `proofbid-00003-kdd`
- Provider: `google.gemini` through Vertex AI ADC
- Model: `gemini-3.5-flash`
- Every run: `STOP`, non-zero usage, unique non-null FunctionTool call IDs,
  provider-manifest hash match, Service/GCS ZIP SHA-256 match, digest-pinned
  revision image, and artifact integrity passed.

## Run matrix

| Route | Task | Execution | Terminal | Missing | Tokens | Provider ms |
|---|---|---|---|---:|---:|---:|
| Green 1 | `task-1e219418489b4e1880f8` | `proofbid-agent-k2bfk` | completed | 0 | 1709 | 15364.958 |
| Green 2 | `task-cee9dba04a86452da569` | `proofbid-agent-xhbbw` | completed | 0 | 1801 | 14370.531 |
| Green 3 | `task-d5743f00cc5c4e8b9731` | `proofbid-agent-56lfh` | completed | 0 | 1705 | 12944.102 |
| Blocked 1 | `task-2587b40b985d4488807f` | `proofbid-agent-qwxbx` | blocked | 1 | 1736 | 15014.734 |
| Blocked 2 | `task-0eac9ab06e2d43f089a4` | `proofbid-agent-98z7v` | blocked | 1 | 1804 | 15586.274 |
| Blocked 3 | `task-8c4af425b1ed443c9e4f` | `proofbid-agent-hgmcb` | blocked | 1 | 1741 | 16699.200 |
| Recovery | `task-61cf08577c9b1605d41e` | `proofbid-agent-fd79q` | completed | 0 | 1757 | 19646.696 |

Green averages are 1738.33 tokens and 14226.53 provider ms. Blocked
averages are 1760.33 tokens and 15766.74 provider ms. These are seven
observations, not production P95 or a cost claim.

Each blocked run contains exactly one missing item with
`PROJECT_AUTHORIZATION_MISSING`, both readiness flags false, high-risk actions
locked, and a complete validated ZIP. The additional
`MANDATORY_REQUIREMENT_RESOLVED` validation code is the deterministic gate that
prevents the unresolved mandatory requirement from being presented as ready;
it is not a second missing item.

The recovery execution was launched by the administrator-only Job command with
`PROOFBID_INJECT_RENDER_FAILURE=1`. Tool sequence 8 recorded
`render_delivery / recoverable_error / RENDER_TRANSIENT`; sequence 9 recorded
exactly one `retry_render` with `retry_of=8`; the task then validated and
completed with 11/11 FunctionTool call IDs.

Individual machine-readable and Markdown receipts are stored beside this file
using each task ID. Raw task downloads, revision/execution payloads and logs
remain in the ignored `.proofbid/evidence-raw/` directory.
