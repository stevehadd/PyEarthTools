# syntax=docker/dockerfile:1
# =============================================================================
# Dockerfile for the aws-site-archive SageMaker Processing Job image.
#
# Builds a container with Python 3.11 and all dependencies required to run
# the demo scripts.
#
# Build:
#   docker build -t aws-site-archive:latest -f deploy/sagemaker/Dockerfile .
#
# Run locally (for testing):
#   docker run --rm \
#       -e AWS_DEFAULT_REGION=eu-west-2 \
#       aws-site-archive:latest \
#       python scripts/demo_mo_global_10km.py --anon --outdir /tmp/output
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="stephen.haddad@metoffice.gov.uk"
LABEL description="aws-site-archive: PyEarthTools data accessors for Met Office AWS ASDI datasets"

# ---------------------------------------------------------------------------
# OS dependencies (eccodes required by cfgrib for GRIB reading)
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        libeccodes-dev \
        libgeos-dev \
        libproj-dev \
        proj-data \
        proj-bin \
        libgdal-dev \
        gdal-bin \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Python environment
# ---------------------------------------------------------------------------
WORKDIR /opt/aws_site_archive

# Copy package files
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/

# Install Python dependencies
# Use --no-cache-dir to keep the image small
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e . \
    # Cartopy data files (for coastlines etc.)
    && python -c "import cartopy; cartopy.config['data_dir']"

# Copy demo scripts and notebooks
COPY scripts/ ./scripts/
COPY notebooks/ ./notebooks/

# ---------------------------------------------------------------------------
# SageMaker Processing Job conventions
# ---------------------------------------------------------------------------
# SageMaker Processing mounts input at /opt/ml/processing/input
# and writes output from /opt/ml/processing/output.
RUN mkdir -p /opt/ml/processing/input /opt/ml/processing/output

# Non-root user for security
RUN useradd --create-home --shell /bin/bash sagemaker
USER sagemaker

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default entrypoint – override when launching the processing job
ENTRYPOINT ["python"]
CMD ["scripts/demo_mo_global_10km.py", "--help"]

