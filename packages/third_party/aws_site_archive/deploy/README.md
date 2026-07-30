# Deploy

This directory contains infrastructure-as-code (IaC) for provisioning the cloud
and HPC resources needed to run `aws_site_archive` demo scripts.

## Sub-directories

### `sagemaker/`

Everything required to run the demo scripts as AWS SageMaker Processing Jobs:

- CloudFormation template (S3 bucket, IAM role, ECR repository, optional Notebook Instance)
- Dockerfile for building a custom container image
- Bash and Python deployment scripts

See [`sagemaker/README.md`](sagemaker/README.md) for step-by-step instructions.

## Quick Deployment

```bash
# Full AWS SageMaker environment
export AWS_REGION=eu-west-2
bash deploy/sagemaker/deploy_environment.sh
```

After deployment, the script will print the environment variables you need to
run the jobs (SAGEMAKER_ROLE, ECR_IMAGE, OUTPUT_S3_PREFIX).

