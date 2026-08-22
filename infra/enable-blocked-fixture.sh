#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
PROOFBID_REGION="${PROOFBID_REGION:-us-central1}"
PROOFBID_SERVICE="${PROOFBID_SERVICE:-proofbid}"
PROOFBID_JOB="${PROOFBID_JOB:-proofbid-agent}"

gcloud config set project "${GOOGLE_CLOUD_PROJECT}"
gcloud run services update "${PROOFBID_SERVICE}" \
  --region "${PROOFBID_REGION}" \
  --update-env-vars '^:^PROOFBID_ALLOWED_FIXTURES=complete_tender,blocked_missing_authorization'
gcloud run jobs update "${PROOFBID_JOB}" \
  --region "${PROOFBID_REGION}" \
  --update-env-vars '^:^PROOFBID_ALLOWED_FIXTURES=complete_tender,blocked_missing_authorization'

gcloud run services describe "${PROOFBID_SERVICE}" \
  --region "${PROOFBID_REGION}" \
  --format='value(status.latestReadyRevisionName)'
