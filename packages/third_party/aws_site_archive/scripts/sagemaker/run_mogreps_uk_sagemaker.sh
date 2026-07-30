#!/bin/bash
# =============================================================================
# run_mogreps_uk_sagemaker.sh
# SageMaker Processing Job wrapper for demo_mogreps_uk.py
# =============================================================================

set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-west-2}"
SAGEMAKER_ROLE="${SAGEMAKER_ROLE:-arn:aws:iam::123456789012:role/SageMakerExecutionRole}"
ECR_IMAGE="${ECR_IMAGE:-}"
INSTANCE_TYPE="${INSTANCE_TYPE:-ml.m5.4xlarge}"
QUERY_TIME="${QUERY_TIME:-2023-06-01T03:00}"
N_MEMBERS="${N_MEMBERS:-6}"
THRESHOLD="${THRESHOLD:-20.0}"
OUTPUT_S3_PREFIX="${OUTPUT_S3_PREFIX:-s3://my-bucket/aws-site-archive/output/mogreps_uk}"
JOB_NAME="aws-mogreps-uk-$(date +%Y%m%d%H%M%S)"

if [[ "${SAGEMAKER_ROLE}" == *"123456789012"* ]]; then
    echo "ERROR: Set SAGEMAKER_ROLE to a valid IAM role ARN."
    exit 1
fi

echo "=== SageMaker Processing Job: ${JOB_NAME} ==="
echo "Query time : ${QUERY_TIME}"
echo "Members    : ${N_MEMBERS}"
echo "Threshold  : ${THRESHOLD} °C"
echo ""

python3 - <<PYEOF
import boto3
import sagemaker
from sagemaker.processing import ScriptProcessor, ProcessingOutput

sess = sagemaker.Session(boto3.Session(region_name="${AWS_REGION}"))
image_uri = "${ECR_IMAGE}" or sagemaker.image_uris.retrieve("sklearn", "${AWS_REGION}", "1.2-1")

processor = ScriptProcessor(
    image_uri=image_uri, command=["python3"],
    instance_type="${INSTANCE_TYPE}", instance_count=1,
    role="${SAGEMAKER_ROLE}", sagemaker_session=sess,
    env={"PYTHONUNBUFFERED": "1"},
)

processor.run(
    code="scripts/demo_mogreps_uk.py",
    job_name="${JOB_NAME}",
    arguments=[
        "--time",      "${QUERY_TIME}",
        "--members",   "${N_MEMBERS}",
        "--threshold", "${THRESHOLD}",
        "--anon",
        "--outdir",    "/opt/ml/processing/output",
    ],
    outputs=[
        ProcessingOutput(
            output_name="figures",
            source="/opt/ml/processing/output",
            destination="${OUTPUT_S3_PREFIX}",
        )
    ],
    wait=True, logs=True,
)
print("Job complete. Outputs at: ${OUTPUT_S3_PREFIX}")
PYEOF

echo "=== Done ==="

