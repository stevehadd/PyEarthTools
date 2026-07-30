#!/bin/bash
# =============================================================================
# run_mo_ukv.sh
#
# Slurm batch submission wrapper for demo_mo_ukv.py on JASMIN.
#
# Usage:
#   sbatch slurm/run_mo_ukv.sh
#   sbatch --export=QUERY_TIME="2023-07-01T06:00",OUTDIR=/scratch/my_output \
#          slurm/run_mo_ukv.sh
# =============================================================================

#SBATCH --job-name=aws_ukv_demo
#SBATCH --partition=short-serial
#SBATCH --time=00:30:00
#SBATCH --mem=8G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

echo "=== Job Info ==="
echo "Job name  : ${SLURM_JOB_NAME}"
echo "Job ID    : ${SLURM_JOB_ID}"
echo "Start     : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Activate conda environment (adjust name/path as needed)
if command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate pet_aws 2>/dev/null || echo "WARNING: pet_aws env not found"
fi

QUERY_TIME="${QUERY_TIME:-2023-06-01T06:00}"
OUTDIR="${OUTDIR:-$(pwd)/output/ukv}"
ANON="${ANON:-true}"

mkdir -p "${OUTDIR}" logs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_SCRIPT="${SCRIPT_DIR}/demo_mo_ukv.py"

echo "=== Run Parameters ==="
echo "Query time : ${QUERY_TIME}"
echo "Output dir : ${OUTDIR}"
echo ""

ANON_FLAG=""
[ "${ANON}" = "true" ] && ANON_FLAG="--anon"

python "${DEMO_SCRIPT}" \
    --time   "${QUERY_TIME}" \
    --outdir "${OUTDIR}" \
    ${ANON_FLAG}

echo "=== Finished at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

