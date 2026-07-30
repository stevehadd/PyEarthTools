# Scripts

This directory contains standalone Python scripts that mirror the Jupyter notebooks
in `../notebooks/`, plus two sets of execution wrappers:

- **`slurm/`** – Slurm batch submission scripts for JASMIN
- **`sagemaker/`** – AWS SageMaker Processing Job wrappers

## Python Demo Scripts

| Script | Dataset | Key outputs |
|--------|---------|-------------|
| `demo_mo_global_10km.py` | Met Office Global 10 km Deterministic | `global_10km_2t.png`, `global_10km_wind.png` |
| `demo_mo_ukv.py` | Met Office UKV (~1.5 km) | `ukv_2t.png`, `ukv_precip.png` |
| `demo_mogreps_global.py` | MOGREPS-G 18-member global ensemble | `mogreps_g_members.png`, `mogreps_g_mean_spread.png` |
| `demo_mogreps_uk.py` | MOGREPS-UK 18-member regional ensemble | `mogreps_uk_2t_mean.png`, `mogreps_uk_prob_warm.png` |

### Running Locally

```bash
# Install the package (from the aws_site_archive root)
pip install -e .

# Run with anonymous S3 access (public datasets)
python scripts/demo_mo_global_10km.py --anon
python scripts/demo_mo_ukv.py --time 2023-06-01T06:00 --anon
python scripts/demo_mogreps_global.py --members 4 --anon
python scripts/demo_mogreps_uk.py --members 6 --threshold 20 --anon
```

Each script accepts `--help` for full usage information.

## Slurm Scripts (`slurm/`)

Submit to the JASMIN compute cluster.
See [`slurm/README.md`](slurm/README.md) for details.

## SageMaker Scripts (`sagemaker/`)

Run as AWS SageMaker Processing Jobs.
See [`sagemaker/README.md`](sagemaker/README.md) for details.

