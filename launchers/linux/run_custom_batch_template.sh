#!/usr/bin/env bash
set -e

# ============================================================
# Custom Aforix batch launcher template
# Copy this file, rename it, and edit BATCH_FILE.
# ============================================================

REPO_DIR="${REPO_DIR:-$HOME/repos/aforix}"
CONDA_ENV="${CONDA_ENV:-aforix}"
CONDA_SH="${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"

# Edit this path to point to your own YAML.
BATCH_FILE="${BATCH_FILE:-configs/batches/user/my_batch.yaml}"

if [ -f "$CONDA_SH" ]; then
    # shellcheck source=/dev/null
    source "$CONDA_SH"
    conda activate "$CONDA_ENV"
else
    conda activate "$CONDA_ENV"
fi

cd "$REPO_DIR"

echo
echo "Running custom Aforix batch:"
echo "$BATCH_FILE"
echo

aforix batch check -b "$BATCH_FILE"
aforix batch plan -b "$BATCH_FILE"
aforix batch run -b "$BATCH_FILE"

echo
echo "Batch finished successfully."
echo "Check runs/batch for manifest.json."