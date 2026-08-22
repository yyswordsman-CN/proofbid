#!/usr/bin/env bash
set -euo pipefail

SOURCE="${1:-https://github.com/yyswordsman-CN/proofbid.git}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
NODE_BIN="${NODE_BIN:-node}"
VERIFY_ROOT="$(mktemp -d /tmp/proofbid-clean-clone.XXXXXX)"
CLONE_DIR="${VERIFY_ROOT}/proofbid"
SERVER_PID=""

cleanup() {
  if [[ -n "${SERVER_PID}" ]]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

git clone --depth 1 "${SOURCE}" "${CLONE_DIR}"
cd "${CLONE_DIR}"

PYTHON_VERSION="$(${PYTHON_BIN} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
NODE_MAJOR="$(${NODE_BIN} -p 'process.versions.node.split(".")[0]')"
[[ "${PYTHON_VERSION}" == "3.12" ]] || { echo "Python 3.12 is required" >&2; exit 2; }
[[ "${NODE_MAJOR}" == "22" ]] || { echo "Node.js 22 is required" >&2; exit 2; }

"${PYTHON_BIN}" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install '.[dev,google,service]'
.venv/bin/python -m pytest -q
.venv/bin/proofbid eval --output build/eval

cd apps/web
npm ci
npx playwright install chromium
npm run build
cd ../..

PYTHONPATH=src .venv/bin/uvicorn proofbid.service:app \
  --host 127.0.0.1 \
  --port 8080 \
  >"${VERIFY_ROOT}/workbench.log" 2>&1 &
SERVER_PID="$!"
for _ in {1..30}; do
  if curl --fail --silent http://127.0.0.1:8080/healthz >"${VERIFY_ROOT}/health.json"; then
    break
  fi
  sleep 1
done
curl --fail --silent http://127.0.0.1:8080/healthz >"${VERIFY_ROOT}/health.json"

cd apps/web
npm run test:e2e
cd ../..

curl --fail --silent \
  --header 'Content-Type: application/json' \
  --data '{"fixture_id":"complete_tender"}' \
  http://127.0.0.1:8080/api/v1/tasks >"${VERIFY_ROOT}/accepted.json"
TASK_ID="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "${VERIFY_ROOT}/accepted.json")"
for _ in {1..30}; do
  curl --fail --silent \
    "http://127.0.0.1:8080/api/v1/tasks/${TASK_ID}" >"${VERIFY_ROOT}/task.json"
  TASK_STATUS="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "${VERIFY_ROOT}/task.json")"
  if [[ "${TASK_STATUS}" == "completed" ]]; then
    break
  fi
  [[ "${TASK_STATUS}" != "failed" ]] || { echo "Workbench task failed" >&2; exit 3; }
  sleep 1
done
[[ "${TASK_STATUS}" == "completed" ]] || { echo "Workbench task timed out" >&2; exit 3; }
curl --fail --silent \
  "http://127.0.0.1:8080/api/v1/tasks/${TASK_ID}/bundle" \
  --output "${VERIFY_ROOT}/proofbid_bundle.zip"
.venv/bin/python -c 'import sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); assert z.testzip() is None' "${VERIFY_ROOT}/proofbid_bundle.zip"

COMMIT_SHA="$(git rev-parse HEAD)"
IMAGE_TAG="proofbid:clean-${COMMIT_SHA:0:12}"
docker build --tag "${IMAGE_TAG}" .
docker run --rm --entrypoint python "${IMAGE_TAG}" \
  -m proofbid.cli agent-run \
  --workspace examples/complete_tender \
  --output /tmp/proofbid-clean-green

[[ -z "$(git status --porcelain)" ]] || { git status --short; exit 4; }
echo "clean_clone_commit=${COMMIT_SHA}"
echo "python=$(${PYTHON_BIN} --version 2>&1)"
echo "node=$(${NODE_BIN} --version)"
echo "image=${IMAGE_TAG}"
echo "task_id=${TASK_ID}"
echo "status=${TASK_STATUS}"
