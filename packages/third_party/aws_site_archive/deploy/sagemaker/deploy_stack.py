#!/usr/bin/env python3
# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.
"""
Deploy the aws-site-archive SageMaker environment via CloudFormation.

This script is an alternative to the bash deploy_environment.sh script.
It uses boto3 to deploy the CloudFormation stack defined in
cloudformation/sagemaker_env.yaml, then optionally builds and pushes
the Docker image.

Usage
-----
    python deploy_stack.py [--region eu-west-2] [--create-notebook]
                            [--stack-name aws-site-archive]

Prerequisites
-------------
    pip install boto3
    aws configure   # or set AWS_PROFILE / AWS_DEFAULT_REGION
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_FILE = SCRIPT_DIR / "cloudformation" / "sagemaker_env.yaml"


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--region", default="eu-west-2",
        help="AWS region. Default: %(default)s"
    )
    parser.add_argument(
        "--stack-name", default="aws-site-archive",
        help="CloudFormation stack name. Default: %(default)s"
    )
    parser.add_argument(
        "--project-name", default="aws-site-archive",
        help="Project name prefix for resource naming. Default: %(default)s"
    )
    parser.add_argument(
        "--create-notebook", action="store_true",
        help="Provision a SageMaker Notebook Instance."
    )
    parser.add_argument(
        "--notebook-instance-type", default="ml.t3.medium",
        help="Notebook instance type. Default: %(default)s"
    )
    return parser.parse_args(argv)


def deploy_stack(
    cf_client,
    stack_name: str,
    template_body: str,
    parameters: list[dict],
) -> dict:
    """
    Create or update a CloudFormation stack.

    Args:
        cf_client: boto3 CloudFormation client.
        stack_name: Name of the stack.
        template_body: YAML/JSON template string.
        parameters: List of CloudFormation parameter dicts.

    Returns:
        dict: Stack outputs.
    """
    kwargs = dict(
        StackName=stack_name,
        TemplateBody=template_body,
        Parameters=parameters,
        Capabilities=["CAPABILITY_NAMED_IAM"],
    )

    try:
        logger.info("Updating existing stack: %s", stack_name)
        cf_client.update_stack(**kwargs)
        waiter = cf_client.get_waiter("stack_update_complete")
    except ClientError as e:
        if "does not exist" in str(e):
            logger.info("Creating new stack: %s", stack_name)
            cf_client.create_stack(**kwargs)
            waiter = cf_client.get_waiter("stack_create_complete")
        elif "No updates are to be performed" in str(e):
            logger.info("Stack is already up to date.")
            waiter = None
        else:
            raise

    if waiter:
        logger.info("Waiting for stack operation to complete …")
        waiter.wait(StackName=stack_name, WaiterConfig={"Delay": 10, "MaxAttempts": 60})
        logger.info("Stack operation complete.")

    response = cf_client.describe_stacks(StackName=stack_name)
    outputs = response["Stacks"][0].get("Outputs", [])
    return {o["OutputKey"]: o["OutputValue"] for o in outputs}


def main(argv=None) -> int:
    """Entry point."""
    args = parse_args(argv)

    session = boto3.Session(region_name=args.region)
    cf = session.client("cloudformation")
    account_id = session.client("sts").get_caller_identity()["Account"]

    logger.info("Account: %s | Region: %s | Stack: %s",
                account_id, args.region, args.stack_name)

    # Read CloudFormation template
    template_body = TEMPLATE_FILE.read_text()

    parameters = [
        {"ParameterKey": "ProjectName",           "ParameterValue": args.project_name},
        {"ParameterKey": "CreateNotebook",        "ParameterValue": "true" if args.create_notebook else "false"},
        {"ParameterKey": "NotebookInstanceType",  "ParameterValue": args.notebook_instance_type},
    ]

    outputs = deploy_stack(cf, args.stack_name, template_body, parameters)

    logger.info("Stack outputs:")
    for key, val in outputs.items():
        logger.info("  %-30s = %s", key, val)

    role_arn = outputs.get("SageMakerRoleArn", "")
    ecr_uri  = outputs.get("ECRRepositoryUri", "")
    bucket   = outputs.get("OutputBucketName", "")

    print("\n" + "=" * 60)
    print("  Deployment complete!")
    print("=" * 60)
    print(f"  IAM Role ARN    : {role_arn}")
    print(f"  ECR URI         : {ecr_uri}:latest")
    print(f"  Output bucket   : s3://{bucket}/")
    print()
    print("  To run a demo job:")
    print(f"    export SAGEMAKER_ROLE={role_arn}")
    print(f"    export ECR_IMAGE={ecr_uri}:latest")
    print(f"    export OUTPUT_S3_PREFIX=s3://{bucket}/output")
    print("    bash scripts/sagemaker/run_mo_global_10km_sagemaker.sh")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

