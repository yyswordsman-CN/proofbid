# Submission freeze checklist

## Rules and eligibility

- [x] Entrant eligibility, employment, residence, IP and prize terms personally confirmed.
- [x] Credits request submitted and receipt saved; approval remains pending.
- [ ] Final Devpost form, judge access and deadline display rechecked.
- [ ] Pre-existing work and third-party dependencies disclosed.

## Runtime evidence

- [x] Real `gemini-3.5-flash` provider evidence captured for local green and blocked FunctionTool routes.
- [x] First post-fix green Cloud Run Job closure reconciled across revision/image digest, provider receipt, logs, GCS and Service ZIP.
- [x] Green case completed three times in Cloud Run Job.
- [x] Blocked case completed three times in Cloud Run Job.
- [x] One real legal recovery route captured.
- [ ] Token, duration and cost samples labeled with sample size; no fake P95.
- [x] Service 202, polling, execution ID, GCS objects and ZIP download verified.
- [x] Cloud revisions, container digest and relevant log timestamps saved for the complete run matrix.

## Repository

- [x] No secret, real customer data, user path, build output or unrelated project asset.
- [x] Public HTTPS clean clone passes `infra/verify-clean-clone.sh` with Python 3.12 and Node 22.
- [x] Apache-2.0, notices, IP disclosure and architecture diagram present.
- [x] Python tests, frontend build, Playwright and 50-case Eval rerun from the public clone.
- [x] Docker build/container green route and Workbench health/202/poll/download pass from that clone.
- [x] English architecture SVG and exact 1920×1080 PNG regenerated with Mermaid CLI 11.16.0.
- [ ] Git commit/tag and source archive hash saved.

## Demo and submission

- [ ] Public English video is 4:00 or shorter and shows the real app running.
- [ ] Video shows Google Cloud backend proof.
- [ ] Public demo works in a clean browser without privileged credentials.
- [ ] Devpost copy contains only verified claims and URLs.
- [ ] Submit early; save screenshot, timestamp, confirmation email and final URLs.
- [ ] Do not change judged repository, video or demo after freeze without documenting why.
