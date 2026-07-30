#!/bin/bash
# =============================================================================
# run_mogreps_global.sh
#
# Slurm batch submission wrapper for demo_mogreps_global.py on JASMIN.
#
# Usage:
#   sbatch slurm/run_mogreps_global.sh
#   sbatch --export=QUERY_TIME="2023-07-01T00:00",N_MEMBERS=18 \
#          slurm/run_mogreps_global.sh
#
# Notes:
#   Loading all 18 members is I/O-intensive. The memory request below is
#   set conservatively; increase if loading full-resolution global ensemble.
# =============================================================================

#SBATCH --job-name=aws_mogreps_g_demo
#SBATCH --partition=short-serial
#SBATCH --time=01:00:00               # Ensemble load can take longer
#SBATCH --mem=32G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4            # Allow parallel S3 reads via fsspec
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

echo "=== Job Info ==="
echo "Job name  : ${SLURM_JOB_NAME}"
echo "Job ID    : ${SLURM_JOB_ID}"
echo "Start     : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

if command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate pet_aws 2>/dev/null || echo "WARNING: pet_aws env not found"
fi

QUERY_TIME="${QUERY_TIME:-2023-06-01T00:00}"
N_MEMBERS="${N_MEMBERS:-4}"   # Increase to 18 for full ensemble
OUTDIR="${OUTDIR:-$(pwd)/output/mogreps_global}"
ANON="${ANON:-true}"

mkdir -p "${OUTDIR}" logs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_SCRIPT="${SCRIPT_DIR}/demo_mogreps_global.py"

echo "=== Run Parameters ==="
echo "Query time : ${QUERY_TIME}"
echo "Members    : ${N_MEMBERS}"
echo "Output dir : ${OUTDIR}"
echo ""

ANON_FLAG=""
[ "${ANON}" = "true" ] && ANON_FLAG="--anon"

python "${DEMO_SCRIPT}" \
    --time    "${QUERY_TIME}" \
    --members "${N_MEMBERS}" \
    --outdir  "${OUTDIR}" \
    ${ANON_FLAG}

echo "=== Finished at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

