# ProofBid — Devpost draft

> Draft only. Replace every bracketed field with verified public evidence before submission.

## Tagline

An evidence-driven autonomous tender agent that completes the preparation package—and refuses to fabricate what is missing.

## Category

The Taskmaster. Additional consideration: Individual / Hobbyist and Best Architectural Design.

## Inspiration

Tender preparation is a high-friction professional task: requirements arrive across documents, every qualification and product claim needs proof, pricing must stay consistent across files, and a missing authorization can invalidate the entire package. Ordinary chat assistants can summarize this work, but they do not reliably finish it or provide an auditable release decision.

## What it does

One synthetic tender event starts a background workflow. A Gemini 3.5 Flash agent built with Google ADK chooses bounded tools to scan inputs, extract requirements, load bidder and product evidence, build a BOM and compliance analysis, run deterministic gates, render Word/Excel/JSON/ZIP artifacts, recover once from a transient renderer failure, and choose the correct complete or blocked terminal branch.

The green case delivers a validated preparation package with both readiness flags true. The blocked case identifies missing project authorization, fabricates nothing, and still delivers a reviewable evidence ledger and missing-item package. Signing, pricing freeze, sending, and submission stay locked.

## How we built it

- Google ADK `Agent`, `Runner`, and bound `FunctionTool` registry;
- Gemini 3.5 Flash through Vertex AI ADC;
- Cloud Run Service for the React/FastAPI event API;
- Cloud Run Job for the autonomous background execution;
- Cloud Storage for task state, Trace, receipts, and delivery artifacts;
- deterministic Python domain logic, openpyxl, and python-docx;
- React/Vite workbench and Playwright desktop/mobile verification.

The model cannot supply paths, shell, SQL, URLs, prices, evidence, or business facts. A server-side state machine enforces tool dependencies, input digests, call budgets, one bounded retry, and deterministic terminal gates. Each tool receipt is chained by SHA-256 and packaged with the final manifest.

## Challenges

The hardest design problem was making Agent autonomy visible without allowing the model to become the source of truth. We separated routing from authority: Gemini makes meaningful workflow choices, while deterministic code owns facts, calculations, rendering, and release. We also had to distinguish a truthful business blocker from a technical task failure so that an incomplete bid can still produce a valuable, validated remediation package.

## Accomplishments

- three genuinely different routes: complete, blocked, and one bounded recovery;
- zero implied submission actions;
- cross-artifact Word/Excel/JSON/ZIP validation and exact-set manifest;
- 50/50 local synthetic Eval cases across structure, missing evidence, product/pricing, prompt injection, and recovery;
- public-safe two-case workbench with no arbitrary upload.

## What we learned

Agent autonomy is strongest when its decision rights are explicit. A constrained tool router can still be meaningfully agentic if it chooses recovery and terminal branches, while typed deterministic tools protect professional truth and safety.

## What's next

After the competition demo, the next product step is versioned public-document parsing and human approval receipts—not automated signing or submission.

## Required evidence before publish

- Repository: `https://github.com/yyswordsman-CN/proofbid`
- Demo: `https://proofbid-um2t63h7ha-uc.a.run.app`
- Video: `[PUBLIC_YOUTUBE_OR_VIMEO_URL]`
- Runtime source commit: `704dbb6d7d7e8114f93bc0dfdf1f18df73267bfd`; submission tag: `[FINAL_TAG]`
- Cloud revisions: `proofbid-00002-jq7` (green-only) and `proofbid-00003-kdd` (two-fixture); image digest `sha256:17bbebcf2c3511b187279ee20cea9ec6359a6a6e763f66cfc0bbc056ce5c8aca`
- Real Gemini/Cloud execution evidence: `docs/evidence/cloud/2026-08-24-verified-closure.md`
