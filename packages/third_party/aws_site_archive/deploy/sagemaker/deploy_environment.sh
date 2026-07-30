#!/bin/bash
# =============================================================================
# deploy_environment.sh
#
# Deploy the complete AWS SageMaker environment required to run the
# aws_site_archive demo scripts.
#
# This script:
#   1. Creates an S3 bucket for output artefacts (if not already present).
#   2. Creates the SageMaker IAM execution role (if not already present).
#   3. Builds and pushes a custom Docker image to Amazon ECR.
#   4. (Optional) Launches a SageMaker Notebook Instance.
#
# Prerequisites
# -------------
#   - AWS CLI ≥ 2.x configured with admin / power-user permissions.
#   - Docker installed and running.
#   - jq installed (sudo apt-get install jq  /  brew install jq).
#
# Usage
# -----
#   bash deploy/sagemaker/deploy_environment.sh
#   ACCOUNT_ID=123456789012 AWS_REGION=eu-west-2 \
#       bash deploy/sagemaker/deploy_environment.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AWS_REGION="${AWS_REGION:-eu-west-2}"
ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
OUTPUT_BUCKET="${OUTPUT_BUCKET:-aws-site-archive-output-${ACCOUNT_ID}}"
ECR_REPO_NAME="${ECR_REPO_NAME:-aws-site-archive}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ROLE_NAME="${ROLE_NAME:-AWSsiteArchiveSageMakerRole}"
CREATE_NOTEBOOK="${CREATE_NOTEBOOK:-false}"  # set to "true" to launch a notebook instance
NOTEBOOK_INSTANCE_NAME="${NOTEBOOK_INSTANCE_NAME:-aws-site-archive-notebook}"
NOTEBOOK_INSTANCE_TYPE="${NOTEBOOK_INSTANCE_TYPE:-ml.t3.medium}"

ECR_REPO_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
IMAGE_URI="${ECR_REPO_URI}:${IMAGE_TAG}"

echo "=========================================================="
echo " AWS Site Archive – SageMaker Environment Deployment"
echo "=========================================================="
echo "Account ID    : ${ACCOUNT_ID}"
echo "Region        : ${AWS_REGION}"
echo "Output bucket : ${OUTPUT_BUCKET}"
echo "ECR repo      : ${ECR_REPO_URI}"
echo "IAM role      : ${ROLE_NAME}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Create output S3 bucket
# ---------------------------------------------------------------------------
echo "[1/5] Checking/creating S3 output bucket: s3://${OUTPUT_BUCKET}"
if aws s3api head-bucket --bucket "${OUTPUT_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
    echo "      Bucket already exists."
else
    aws s3api create-bucket \
        --bucket "${OUTPUT_BUCKET}" \
        --region "${AWS_REGION}" \
        --create-bucket-configuration LocationConstraint="${AWS_REGION}"
    echo "      Bucket created."
fi

# Enable versioning and block public access
aws s3api put-bucket-versioning \
    --bucket "${OUTPUT_BUCKET}" \
    --versioning-configuration Status=Enabled
aws s3api put-public-access-block \
    --bucket "${OUTPUT_BUCKET}" \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "      Versioning enabled; public access blocked."

# ---------------------------------------------------------------------------
# Step 2: Create IAM execution role
# ---------------------------------------------------------------------------
echo "[2/5] Checking/creating IAM execution role: ${ROLE_NAME}"

TRUST_POLICY=$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "sagemaker.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
)

if aws iam get-role --role-name "${ROLE_NAME}" 2>/dev/null; then
    echo "      Role already exists."
else
    aws iam create-role \
        --role-name "${ROLE_NAME}" \
        --assume-role-policy-document "${TRUST_POLICY}" \
        --description "SageMaker execution role for aws-site-archive"
    echo "      Role created."
fi

# Attach managed policies
for POLICY in AmazonSageMakerFullAccess AmazonS3ReadOnlyAccess; do
    aws iam attach-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-arn "arn:aws:iam::aws:policy/${POLICY}" 2>/dev/null || true
done

# Allow writing to our output bucket
aws iam put-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-name "AllowOutputBucketWrite" \
    --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [{
            \"Effect\": \"Allow\",
            \"Action\": [\"s3:PutObject\",\"s3:PutObjectAcl\"],
            \"Resource\": \"arn:aws:s3:::${OUTPUT_BUCKET}/*\"
        }]
    }"

ROLE_ARN=$(aws iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text)
echo "      Role ARN: ${ROLE_ARN}"

# ---------------------------------------------------------------------------
# Step 3: Create ECR repository
# ---------------------------------------------------------------------------
echo "[3/5] Checking/creating ECR repository: ${ECR_REPO_NAME}"
aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" \
    --region "${AWS_REGION}" 2>/dev/null \
    || aws ecr create-repository \
        --repository-name "${ECR_REPO_NAME}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true
echo "      ECR repository ready."

# ---------------------------------------------------------------------------
# Step 4: Build and push Docker image
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

if [ ! -f "${DOCKERFILE}" ]; then
    echo "ERROR: Dockerfile not found at ${DOCKERFILE}"
    exit 1
fi

echo "[4/5] Building Docker image …"
docker build -t "${ECR_REPO_NAME}:${IMAGE_TAG}" -f "${DOCKERFILE}" "${SCRIPT_DIR}/../../"

echo "      Authenticating with ECR …"
aws ecr get-login-password --region "${AWS_REGION}" \
    | docker login --username AWS --password-stdin \
        "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "      Pushing image to ECR …"
docker tag "${ECR_REPO_NAME}:${IMAGE_TAG}" "${IMAGE_URI}"
docker push "${IMAGE_URI}"
echo "      Image pushed: ${IMAGE_URI}"

# ---------------------------------------------------------------------------
# Step 5: (Optional) Create Notebook Instance
# ---------------------------------------------------------------------------
if [ "${CREATE_NOTEBOOK}" = "true" ]; then
    echo "[5/5] Creating SageMaker Notebook Instance: ${NOTEBOOK_INSTANCE_NAME}"
    aws sagemaker create-notebook-instance \
        --notebook-instance-name "${NOTEBOOK_INSTANCE_NAME}" \
        --instance-type "${NOTEBOOK_INSTANCE_TYPE}" \
        --role-arn "${ROLE_ARN}" \
        --region "${AWS_REGION}" \
        --default-code-repository "" \
        2>/dev/null && echo "      Notebook instance created." \
        || echo "      Notebook instance may already exist – skipping."
else
    echo "[5/5] Skipping notebook instance (CREATE_NOTEBOOK != true)."
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
cat <<SUMMARY

==========================================
 Deployment complete!
==========================================
Output S3 bucket : s3://${OUTPUT_BUCKET}/
IAM role ARN     : ${ROLE_ARN}
Docker image     : ${IMAGE_URI}

Next steps:
1. Set these environment variables before running the SageMaker wrappers:
   export SAGEMAKER_ROLE=${ROLE_ARN}
   export ECR_IMAGE=${IMAGE_URI}
   export OUTPUT_S3_PREFIX=s3://${OUTPUT_BUCKET}/output

2. Submit a job:
   bash scripts/sagemaker/run_mo_global_10km_sagemaker.sh
SUMMARY

