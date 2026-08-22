# Third-party dependencies

ProofBid is licensed under Apache-2.0. Runtime and development dependencies retain their own licenses.

| Package | Intended version range | License | Use |
|---|---:|---|---|
| Google Agent Development Kit | 2.7.1 | Apache-2.0 | ADK Agent, Runner, FunctionTool and sessions |
| Google Gen AI SDK | 2.18.1 | Apache-2.0 | Gemini model types and provider metadata |
| FastAPI | 0.116–0.x | MIT | Task API and health endpoint |
| Uvicorn | 0.35–0.x | BSD-3-Clause | ASGI server |
| Google Auth | 2.40–2.x | Apache-2.0 | ADC and authenticated Cloud Run v2 calls |
| Google Cloud Storage | 3.2–3.x | Apache-2.0 | Task state and delivery objects |
| Pydantic | 2.12–2.x | MIT | Request and planning contracts |
| openpyxl | 3.1–3.x | MIT | Excel rendering and validation |
| python-docx | 1.2–1.x | MIT | Word rendering and validation |
| React / React DOM | current lockfile | MIT | Public workbench |
| Vite | current lockfile | MIT | Frontend build |
| Playwright | current lockfile | Apache-2.0 | Desktop and mobile UI verification |

The authoritative resolved JavaScript versions are in `apps/web/package-lock.json`. Python production dependencies are constrained in `pyproject.toml`; a fully resolved deployment record must be generated with the final container digest before submission.
