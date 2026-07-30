# Notebooks

This directory contains Jupyter notebooks that demonstrate how to use the
`site_archive_aws` package to access and visualise Met Office NWP datasets
from the [AWS Sustainable Data Initiative (ASDI)](https://registry.opendata.aws/uk-met-office/).

## Contents

| Notebook | Dataset | Key concepts |
|----------|---------|--------------|
| `01_mo_global_10km.ipynb` | Met Office Global 10 km Deterministic | Global maps, wind barbs, multi-variable loading |
| `02_mo_ukv.ipynb` | Met Office UKV (~1.5 km) | UK regional maps, precipitation, rotated-pole grids |
| `03_mogreps_global.ipynb` | MOGREPS-G 18-member global ensemble | Member comparison, ensemble mean & spread |
| `04_mogreps_uk.ipynb` | MOGREPS-UK 18-member UK regional ensemble | Probabilistic maps, P(T > threshold) |

## Running the Notebooks

### Locally

```bash
# Install the package and dependencies (from the aws_site_archive root)
pip install -e ".[dev]"

# Launch Jupyter
jupyter lab
```

### On JASMIN

Use the JASMIN Notebook Service at https://notebooks.jasmin.ac.uk/ or submit via Slurm:

```bash
# See scripts/slurm/ for batch submission wrappers
```

### On AWS SageMaker

Upload this directory to an S3 bucket, then launch a SageMaker Notebook Instance
pointing at that bucket. See `deploy/sagemaker/` for automated setup scripts.

## Output Figures

Each notebook saves PNG figures to the working directory:

| Notebook | Output files |
|----------|-------------|
| `01_mo_global_10km.ipynb` | `global_10km_2t.png`, `global_10km_wind.png` |
| `02_mo_ukv.ipynb` | `ukv_2t.png`, `ukv_precip.png` |
| `03_mogreps_global.ipynb` | `mogreps_g_members.png`, `mogreps_g_mean_spread.png` |
| `04_mogreps_uk.ipynb` | `mogreps_uk_2t_mean.png`, `mogreps_uk_prob_warm.png` |

