#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT to the isolated competition project}"
: "${PROOFBID_TASK_BUCKET:?Set PROOFBID_TASK_BUCKET to a globally unique bucket name}"

PROOFBID_REGION="${PROOFBID_REGION:-us-central1}"
PROOFBID_REPOSITORY="${PROOFBID_REPOSITORY:-proofbid}"
PROOFBID_IMAGE="${PROOFBID_REGION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${PROOFBID_REPOSITORY}/proofbid"
PROOFBID_SERVICE_SA="proofbid-service@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
PROOFBID_JOB_SA="proofbid-job@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

gcloud config set project "${GOOGLE_CLOUD_PROJECT}"
gcloud services enable \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com

gcloud artifacts repositories describe "${PROOFBID_REPOSITORY}" \
  --location "${PROOFBID_REGION}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${PROOFBID_REPOSITORY}" \
    --location "${PROOFBID_REGION}" \
    --repository-format docker

gcloud storage buckets describe "gs://${PROOFBID_TASK_BUCKET}" >/dev/null 2>&1 || \
  gcloud storage buckets create "gs://${PROOFBID_TASK_BUCKET}" \
    --location "${PROOFBID_REGION}" \
    --uniform-bucket-level-access
gcloud storage buckets update "gs://${PROOFBID_TASK_BUCKET}" \
  --lifecycle-file infra/gcs-lifecycle.json

gcloud iam service-accounts describe "${PROOFBID_SERVICE_SA}" >/dev/null 2>&1 || \
  gcloud iam service-accounts create proofbid-service \
    --display-name "ProofBid Cloud Run service"
gcloud iam service-accounts describe "${PROOFBID_JOB_SA}" >/dev/null 2>&1 || \
  gcloud iam service-accounts create proofbid-job \
    --display-name "ProofBid Cloud Run job"

gcloud storage buckets add-iam-policy-binding "gs://${PROOFBID_TASK_BUCKET}" \
  --member "serviceAccount:${PROOFBID_SERVICE_SA}" \
  --role roles/storage.objectUser
gcloud storage buckets add-iam-policy-binding "gs://${PROOFBID_TASK_BUCKET}" \
  --member "serviceAccount:${PROOFBID_JOB_SA}" \
  --role roles/storage.objectUser
gcloud projects add-iam-policy-binding "${GOOGLE_CLOUD_PROJECT}" \
  --member "serviceAccount:${PROOFBID_JOB_SA}" \
  --role roles/aiplatform.user
gcloud builds submit --tag "${PROOFBID_IMAGE}"

gcloud run jobs deploy proofbid-agent \
  --image "${PROOFBID_IMAGE}" \
  --region "${PROOFBID_REGION}" \
  --service-account "${PROOFBID_JOB_SA}" \
  --command python \
  --args=-m,proofbid.task_worker \
  --tasks 1 \
  --parallelism 1 \
  --max-retries 0 \
  --task-timeout 10m \
  --set-env-vars "PROOFBID_STORAGE_BACKEND=gcs,PROOFBID_TASK_BUCKET=${PROOFBID_TASK_BUCKET},PROOFBID_AGENT_MODE=google,PROOFBID_GEMINI_MODEL=gemini-3.5-flash,PROOFBID_GEMINI_AUTH=vertex_ai,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=global"

gcloud run jobs add-iam-policy-binding proofbid-agent \
  --region "${PROOFBID_REGION}" \
  --member "serviceAccount:${PROOFBID_SERVICE_SA}" \
  --role roles/run.jobsExecutorWithOverrides

gcloud run deploy proofbid \
  --image "${PROOFBID_IMAGE}" \
  --region "${PROOFBID_REGION}" \
  --service-account "${PROOFBID_SERVICE_SA}" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 20 \
  --timeout 60 \
  --set-env-vars "PROOFBID_STORAGE_BACKEND=gcs,PROOFBID_TASK_BUCKET=${PROOFBID_TASK_BUCKET},PROOFBID_CLOUD_RUN_JOB=proofbid-agent,PROOFBID_CLOUD_RUN_LOCATION=${PROOFBID_REGION},PROOFBID_PUBLIC_DEMO=1,PROOFBID_DAILY_DEMO_QUOTA=40,GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}"
