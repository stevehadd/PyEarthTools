# Slurm Batch Scripts

This directory contains Slurm batch submission wrappers for running the AWS ASDI
demo scripts on the [JASMIN](https://www.jasmin.ac.uk/) scientific computing cluster.

## Prerequisites

1. An active JASMIN account with access to the `short-serial` (or equivalent) partition.
2. A conda environment named `pet_aws` with `site_archive_aws` installed:

   ```bash
   conda create -n pet_aws python=3.11
   conda activate pet_aws
   pip install -e /path/to/aws_site_archive
   ```

3. (Optional) AWS credentials configured in `~/.aws/credentials` if you need
   authenticated access.  For the public Met Office ASDI buckets, anonymous
   access (`anon=true`) is sufficient.

## Scripts

| Script | Demo | Partition | Memory |
|--------|------|-----------|--------|
| `run_mo_global_10km.sh` | Global 10 km deterministic | `short-serial` | 8 GB |
| `run_mo_ukv.sh` | UKV (~1.5 km) model | `short-serial` | 8 GB |
| `run_mogreps_global.sh` | MOGREPS-G global ensemble | `short-serial` | 32 GB |
| `run_mogreps_uk.sh` | MOGREPS-UK regional ensemble | `short-serial` | 32 GB |

## Usage

```bash
# Simple submission (all defaults)
sbatch slurm/run_mo_global_10km.sh

# Override parameters via --export
sbatch \
  --export=QUERY_TIME="2023-07-01T00:00",OUTDIR=/work/scratch-pw/myoutput,N_MEMBERS=18 \
  slurm/run_mogreps_global.sh

# Check job status
squeue -u $USER
```

## Environment Variables

Each script respects the following environment variables (all have sensible defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `QUERY_TIME` | `2023-06-01T00:00` | Model initialisation time |
| `OUTDIR` | `./output/<model>/` | Directory for output PNG files |
| `ANON` | `true` | Use anonymous S3 access (`true`/`""`) |
| `N_MEMBERS` | `4` or `6` | Number of ensemble members (ensemble scripts) |
| `THRESHOLD` | `20.0` | Temperature threshold for probability plot (MOGREPS-UK) |

## Logs

Job stdout and stderr are written to the `logs/` directory (created automatically)
as `<jobname>_<jobid>.out` and `.err` files.

## JASMIN-specific Notes

- JASMIN does not have direct internet access from compute nodes.
  The S3 data is accessed via the JASMIN object store or an STFC network route
  that allows access to `eu-west-2`.  Check with the JASMIN helpdesk if you
  encounter connectivity issues.
- If using the JASMIN object store mirror of Met Office data, update the
  `ROOT_DIRECTORIES` in your `~/.pyearthtoolsconfig`.

