# SageMaker Execution Wrappers

This directory contains bash wrappers that submit the demo Python scripts as
[AWS SageMaker Processing Jobs](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job.html).

## Quick Start

```bash
# Set your IAM execution role
export SAGEMAKER_ROLE=arn:aws:iam::<account_id>:role/<role_name>

# Run the Global 10 km demo
bash sagemaker/run_mo_global_10km_sagemaker.sh

# Run MOGREPS-G with custom parameters
QUERY_TIME="2023-07-01T00:00" N_MEMBERS=8 \
    bash sagemaker/run_mogreps_global_sagemaker.sh
```

## Prerequisites

1. **AWS CLI** configured: `aws configure`
2. **Python dependencies** installed: `pip install sagemaker boto3`
3. **IAM execution role** with:
   - `AmazonSageMakerFullAccess` (or equivalent minimal permissions)
   - S3 read access to the Met Office ASDI buckets
   - S3 write access to your output bucket
4. **Output S3 bucket** – set `OUTPUT_S3_PREFIX` to your own bucket path.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `eu-west-2` | AWS region (Met Office data is in London) |
| `SAGEMAKER_ROLE` | *(required)* | IAM execution role ARN |
| `ECR_IMAGE` | *(auto)* | Custom Docker image URI; defaults to AWS managed scikit-learn image |
| `INSTANCE_TYPE` | `ml.m5.xlarge` | SageMaker instance type |
| `QUERY_TIME` | `2023-06-01T00:00` | Model initialisation time |
| `OUTPUT_S3_PREFIX` | `s3://my-bucket/…` | S3 destination for output figures |
| `N_MEMBERS` | 4 or 6 | Ensemble members to load (ensemble scripts only) |
| `THRESHOLD` | `20.0` | Temperature threshold in °C (MOGREPS-UK only) |

## Scripts

| Script | Instance type | Notes |
|--------|---------------|-------|
| `run_mo_global_10km_sagemaker.sh` | `ml.m5.xlarge` | Single-variable, fast |
| `run_mo_ukv_sagemaker.sh` | `ml.m5.xlarge` | UK-domain, rotated-pole coords |
| `run_mogreps_global_sagemaker.sh` | `ml.m5.4xlarge` | Multi-member; use larger instance |
| `run_mogreps_uk_sagemaker.sh` | `ml.m5.4xlarge` | Multi-member; UK-domain |

## Using a Custom Docker Image

For production use, build a custom image with all dependencies pre-installed
(see `deploy/sagemaker/` for a Dockerfile and ECR push scripts):

```bash
export ECR_IMAGE=<account_id>.dkr.ecr.eu-west-2.amazonaws.com/aws-site-archive:latest
bash sagemaker/run_mo_global_10km_sagemaker.sh
```

