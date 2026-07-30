#!/bin/bash
# =============================================================================
# run_mo_global_10km.sh
#
# Slurm batch submission wrapper for demo_mo_global_10km.py on the
# JASMIN scientific computing cluster.
#
# Usage (from the scripts/ directory):
#   sbatch slurm/run_mo_global_10km.sh
#
# To override the query time or output directory:
#   sbatch --export=QUERY_TIME="2023-07-01T12:00",OUTDIR=/work/scratch-pw/myoutput \
#          slurm/run_mo_global_10km.sh
#
# JASMIN documentation: https://help.jasmin.ac.uk/
# =============================================================================

#SBATCH --job-name=aws_global10km_demo
#SBATCH --partition=short-serial      # Use 'high-mem' for larger jobs
#SBATCH --time=00:30:00               # Wall-clock limit HH:MM:SS
#SBATCH --mem=8G                      # Memory per node
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/%x_%j.out      # stdout log: jobname_jobid.out
#SBATCH --error=logs/%x_%j.err       # stderr log: jobname_jobid.err

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
set -euo pipefail

echo "=== Job Info ==="
echo "Job name    : ${SLURM_JOB_NAME}"
echo "Job ID      : ${SLURM_JOB_ID}"
echo "Node        : ${SLURM_NODELIST:-unknown}"
echo "Start time  : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Load a conda environment that has the aws_site_archive package installed.
# Adjust the environment name / module load command to match your JASMIN setup.
# Option 1 – module system:
#   module load jaspy/3.11/r20240101
# Option 2 – conda/mamba:
#   source /path/to/mambaforge/etc/profile.d/conda.sh
#   conda activate pet_aws

if command -v conda &>/dev/null; then
    # shellcheck disable=SC1090
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate pet_aws 2>/dev/null || echo "WARNING: pet_aws env not found; using current Python"
fi

# ---------------------------------------------------------------------------
# Parameters (override with --export when calling sbatch)
# ---------------------------------------------------------------------------
QUERY_TIME="${QUERY_TIME:-2023-06-01T00:00}"
OUTDIR="${OUTDIR:-$(pwd)/output/global_10km}"
ANON="${ANON:-true}"    # set to "" to use AWS credentials

mkdir -p "${OUTDIR}" logs

# ---------------------------------------------------------------------------
# Resolve the script location relative to this wrapper
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_SCRIPT="${SCRIPT_DIR}/demo_mo_global_10km.py"

echo "=== Run Parameters ==="
echo "Query time  : ${QUERY_TIME}"
echo "Output dir  : ${OUTDIR}"
echo "Script      : ${DEMO_SCRIPT}"
echo ""

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
ANON_FLAG=""
if [ "${ANON}" = "true" ]; then
    ANON_FLAG="--anon"
fi

python "${DEMO_SCRIPT}" \
    --time  "${QUERY_TIME}" \
    --outdir "${OUTDIR}" \
    ${ANON_FLAG}

echo ""
echo "=== Finished at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

