# Deploy – SageMaker Infrastructure

This directory contains everything needed to provision the AWS infrastructure
for running `aws_site_archive` demo scripts on SageMaker.

## What Gets Deployed

| Resource | Description |
|----------|-------------|
| **S3 bucket** | Stores job output figures (PNG files) |
| **IAM role** | SageMaker execution role with S3 and ECR permissions |
| **ECR repository** | Stores the custom Docker image |
| **SageMaker Notebook Instance** | *(optional)* Interactive Jupyter environment |

## Deployment Options

### Option A: All-in-one bash script

```bash
# Set your AWS region and (optionally) account ID
export AWS_REGION=eu-west-2
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Deploy everything (S3, IAM, ECR, Docker build + push)
bash deploy/sagemaker/deploy_environment.sh

# With a Notebook Instance:
CREATE_NOTEBOOK=true bash deploy/sagemaker/deploy_environment.sh
```

### Option B: CloudFormation only (no Docker build)

```bash
# Deploy the CloudFormation stack
aws cloudformation deploy \
    --template-file deploy/sagemaker/cloudformation/sagemaker_env.yaml \
    --stack-name aws-site-archive \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides CreateNotebook=false

# Get outputs
aws cloudformation describe-stacks \
    --stack-name aws-site-archive \
    --query 'Stacks[0].Outputs'
```

### Option C: Python script (boto3)

```bash
pip install boto3

# Basic deployment
python deploy/sagemaker/deploy_stack.py --region eu-west-2

# With a Notebook Instance
python deploy/sagemaker/deploy_stack.py \
    --region eu-west-2 \
    --create-notebook \
    --notebook-instance-type ml.t3.large
```

## Files

| File | Description |
|------|-------------|
| `deploy_environment.sh` | All-in-one bash deployment script |
| `deploy_stack.py` | Python/boto3 CloudFormation deployment |
| `Dockerfile` | Container image definition for Processing Jobs |
| `cloudformation/sagemaker_env.yaml` | CloudFormation template |

## Tear-down

```bash
# Delete the CloudFormation stack (does NOT delete the S3 bucket by default)
aws cloudformation delete-stack --stack-name aws-site-archive

# To also delete the output bucket (WARNING: irreversible)
aws s3 rb s3://aws-site-archive-output-<account_id> --force
```

## Cost Considerations

- **S3**: Negligible storage cost for PNG outputs.
- **SageMaker Processing Jobs**: Billed per second of instance use; jobs typically
  finish in 1–5 minutes.
- **ECR**: Small storage cost for the Docker image (~1 GB).
- **Notebook Instance**: Billed per hour; remember to stop it when not in use.

Recommended: use `ml.m5.xlarge` or smaller for single-dataset jobs, and
`ml.m5.4xlarge` for full-ensemble loads.

