#!/bin/bash
# =============================================================================
# run_mo_global_10km_sagemaker.sh
#
# Wrapper to run demo_mo_global_10km.py as an AWS SageMaker Processing Job.
#
# Prerequisites
# -------------
# 1. AWS CLI configured: aws configure
# 2. boto3 / sagemaker SDK installed: pip install sagemaker boto3
# 3. An IAM execution role with S3 read access and SageMaker permissions.
#    Set SAGEMAKER_ROLE below or export it as an environment variable.
# 4. The demo script uploaded to S3 (see deploy/sagemaker/ for automation).
#
# Usage
# -----
#   bash sagemaker/run_mo_global_10km_sagemaker.sh
#   QUERY_TIME="2023-07-01T00:00" bash sagemaker/run_mo_global_10km_sagemaker.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration – override via environment or edit defaults below
# ---------------------------------------------------------------------------
AWS_REGION="${AWS_REGION:-eu-west-2}"
SAGEMAKER_ROLE="${SAGEMAKER_ROLE:-arn:aws:iam::123456789012:role/SageMakerExecutionRole}"
ECR_IMAGE="${ECR_IMAGE:-}"                      # Custom image URI (optional)
INSTANCE_TYPE="${INSTANCE_TYPE:-ml.m5.xlarge}"
QUERY_TIME="${QUERY_TIME:-2023-06-01T00:00}"
OUTPUT_S3_PREFIX="${OUTPUT_S3_PREFIX:-s3://my-bucket/aws-site-archive/output/global_10km}"
JOB_NAME="aws-global10km-$(date +%Y%m%d%H%M%S)"

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
if [[ "${SAGEMAKER_ROLE}" == *"123456789012"* ]]; then
    echo "ERROR: Please set SAGEMAKER_ROLE to a valid IAM role ARN."
    echo "       export SAGEMAKER_ROLE=arn:aws:iam::<account_id>:role/<role_name>"
    exit 1
fi

echo "=== SageMaker Processing Job: ${JOB_NAME} ==="
echo "Region        : ${AWS_REGION}"
echo "Role          : ${SAGEMAKER_ROLE}"
echo "Instance type : ${INSTANCE_TYPE}"
echo "Query time    : ${QUERY_TIME}"
echo "Output prefix : ${OUTPUT_S3_PREFIX}"
echo ""

# ---------------------------------------------------------------------------
# Submit via Python SDK (inline)
# The sagemaker Python SDK is used here for flexibility.
# Alternatively, use the AWS CLI: aws sagemaker create-processing-job ...
# ---------------------------------------------------------------------------
python3 - <<PYEOF
import boto3
import sagemaker
from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput

sess = sagemaker.Session(boto3.Session(region_name="${AWS_REGION}"))

# Use a pre-built AWS-managed Python image if no custom image is specified
image_uri = "${ECR_IMAGE}" or sagemaker.image_uris.retrieve(
    framework="sklearn",
    region="${AWS_REGION}",
    version="1.2-1",
)

processor = ScriptProcessor(
    image_uri=image_uri,
    command=["python3"],
    instance_type="${INSTANCE_TYPE}",
    instance_count=1,
    role="${SAGEMAKER_ROLE}",
    sagemaker_session=sess,
    env={
        "PYTHONUNBUFFERED": "1",
        "QUERY_TIME": "${QUERY_TIME}",
    },
)

processor.run(
    code="scripts/demo_mo_global_10km.py",      # Path relative to source_dir or S3
    job_name="${JOB_NAME}",
    arguments=[
        "--time", "${QUERY_TIME}",
        "--anon",                                # Public data; no extra creds needed
        "--outdir", "/opt/ml/processing/output",
    ],
    outputs=[
        ProcessingOutput(
            output_name="figures",
            source="/opt/ml/processing/output",
            destination="${OUTPUT_S3_PREFIX}",
        )
    ],
    wait=True,
    logs=True,
)

print(f"Job complete. Outputs at: ${OUTPUT_S3_PREFIX}")
PYEOF

echo "=== Done ==="

