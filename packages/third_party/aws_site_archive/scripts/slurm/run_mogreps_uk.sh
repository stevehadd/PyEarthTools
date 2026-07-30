#!/bin/bash
# =============================================================================
# run_mogreps_uk.sh
#
# Slurm batch submission wrapper for demo_mogreps_uk.py on JASMIN.
#
# Usage:
#   sbatch slurm/run_mogreps_uk.sh
#   sbatch --export=QUERY_TIME="2023-07-01T03:00",N_MEMBERS=18,THRESHOLD=25 \
#          slurm/run_mogreps_uk.sh
# =============================================================================

#SBATCH --job-name=aws_mogreps_uk_demo
#SBATCH --partition=short-serial
#SBATCH --time=01:00:00
#SBATCH --mem=32G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
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

QUERY_TIME="${QUERY_TIME:-2023-06-01T03:00}"
N_MEMBERS="${N_MEMBERS:-6}"
THRESHOLD="${THRESHOLD:-20.0}"
OUTDIR="${OUTDIR:-$(pwd)/output/mogreps_uk}"
ANON="${ANON:-true}"

mkdir -p "${OUTDIR}" logs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_SCRIPT="${SCRIPT_DIR}/demo_mogreps_uk.py"

echo "=== Run Parameters ==="
echo "Query time : ${QUERY_TIME}"
echo "Members    : ${N_MEMBERS}"
echo "Threshold  : ${THRESHOLD} °C"
echo "Output dir : ${OUTDIR}"
echo ""

ANON_FLAG=""
[ "${ANON}" = "true" ] && ANON_FLAG="--anon"

python "${DEMO_SCRIPT}" \
    --time      "${QUERY_TIME}" \
    --members   "${N_MEMBERS}" \
    --threshold "${THRESHOLD}" \
    --outdir    "${OUTDIR}" \
    ${ANON_FLAG}

echo "=== Finished at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

