#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
PROOFBID_REGION="${PROOFBID_REGION:-us-central1}"
PROOFBID_JOB="${PROOFBID_JOB:-proofbid-agent}"
PROOFBID_TASK_ID="${PROOFBID_TASK_ID:-task-$(openssl rand -hex 10)}"

if [[ ! "${PROOFBID_TASK_ID}" =~ ^task-[0-9a-f]{20}$ ]]; then
  echo "PROOFBID_TASK_ID must match task-[0-9a-f]{20}" >&2
  exit 2
fi

gcloud config set project "${GOOGLE_CLOUD_PROJECT}"
gcloud run jobs execute "${PROOFBID_JOB}" \
  --region "${PROOFBID_REGION}" \
  --update-env-vars "PROOFBID_TASK_ID=${PROOFBID_TASK_ID},PROOFBID_FIXTURE_ID=complete_tender,PROOFBID_INJECT_RENDER_FAILURE=1" \
  --format='value(metadata.name)'

echo "task_id=${PROOFBID_TASK_ID}"
