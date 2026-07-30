# PyEarthTools AWS Site Archive

A [PyEarthTools](https://pyearthtools.readthedocs.io) plugin that provides data accessors for Met Office and partner
Numerical Weather Prediction (NWP) datasets available via the
[AWS Sustainable Data Initiative (ASDI)](https://registry.opendata.aws/).

## Datasets

| Accessor | Description | S3 Bucket | Temporal Resolution |
|----------|-------------|-----------|---------------------|
| `MOGlobal10km` | Met Office Global 10 km deterministic NWP | `met-office-atmospheric-model-data` | 6-hourly (T+0 to T+54) |
| `MOUKV` | Met Office UKV (variable-resolution) model | `met-office-atmospheric-model-data` | 1-hourly (T+0 to T+36) |
| `MOGREPSGlobal` | Met Office MOGREPS-G 18-member global ensemble | `met-office-ensemble-model-data` | 6-hourly |
| `MOGREPSUK` | Met Office MOGREPS-UK 18-member regional ensemble | `met-office-ensemble-model-data` | 3-hourly |

All datasets are freely available on AWS S3 in the `eu-west-2` (London) region as part of the
[Met Office ASDI programme](https://registry.opendata.aws/uk-met-office/).

## Requirements

- Python ≥ 3.10
- An AWS account (for authenticated access; public datasets may be read anonymously)
- `pyearthtools-data >= 0.1.0`
- See `requirements.txt` for a full list of dependencies

## Installation

```bash
pip install .
# or for development:
pip install -e ".[dev]"
```

## Quick Start

```python
import site_archive_aws

# Read Met Office Global 10km 2-m temperature at a specific time
accessor = site_archive_aws.MOGlobal10km("2t")
data = accessor["2023-06-01T00:00"]
print(data)

# Read MOGREPS-G ensemble 10-m wind speed (all members)
ensemble = site_archive_aws.MOGREPSGlobal(["10u", "10v"])
data = ensemble["2023-06-01T00:00"]
print(data)
```

## Configuration

AWS credentials are loaded from the standard locations (environment variables, `~/.aws/credentials`, IAM roles).
For public (anonymous) access to open datasets, no credentials are required.

You can configure the S3 bucket roots in your `~/.pyearthtoolsconfig` file:

```ini
[aws]
MOGlobal10km = s3://met-office-atmospheric-model-data/global-deterministic/
MOUKV = s3://met-office-atmospheric-model-data/uk-deterministic/
MOGREPSGlobal = s3://met-office-ensemble-model-data/global-ensemble/
MOGREPSUK = s3://met-office-ensemble-model-data/uk-ensemble/
```

## Directory Structure

```
aws_site_archive/
├── pyproject.toml              # Package metadata and build configuration
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Development / notebook dependencies
├── README.md                   # This file
├── src/
│   └── site_archive_aws/       # Main Python package
│       ├── __init__.py
│       ├── utilities.py        # Shared helpers (S3 caching, postprocessing)
│       ├── mo_global_10km.py   # Met Office Global 10km accessor
│       ├── mo_ukv.py           # Met Office UKV accessor
│       ├── mogreps_global.py   # MOGREPS-G ensemble accessor
│       ├── mogreps_uk.py       # MOGREPS-UK ensemble accessor
│       └── ancilliary/         # Variable lists, metadata constants
├── notebooks/                  # Jupyter notebooks demonstrating each dataset
├── scripts/                    # Standalone Python demo scripts
│   ├── slurm/                  # Slurm batch-submission wrappers (JASMIN)
│   └── sagemaker/              # AWS SageMaker execution wrappers
└── deploy/                     # Infrastructure-as-code for AWS SageMaker
    └── sagemaker/
```

## Licence

(C) British Crown Copyright 2024–2026, Met Office. See `LICENSE` for details.

