#!/usr/bin/env bash
set -e

# ============================================================
# Run any Aforix batch YAML file
# ============================================================

REPO_DIR="${REPO_DIR:-$HOME/repos/aforix}"
CONDA_ENV="${CONDA_ENV:-aforix}"
CONDA_SH="${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"

if [ -f "$CONDA_SH" ]; then
    # shellcheck source=/dev/null
    source "$CONDA_SH"
    conda activate "$CONDA_ENV"
else
    conda activate "$CONDA_ENV"
fi

cd "$REPO_DIR"

BATCH_FILE="${1:-}"

if [ -z "$BATCH_FILE" ]; then
    echo
    echo "No batch YAML file was provided."
    read -r -p "Batch YAML path: " BATCH_FILE
fi

if [ -z "$BATCH_FILE" ]; then
    echo "No batch file selected. Exiting."
    exit 1
fi

echo
echo "==========================================================="
echo "Aforix batch file"
echo "$BATCH_FILE"
echo "==========================================================="
echo

echo "[1/3] Checking batch..."
aforix batch check -b "$BATCH_FILE"

echo
echo "[2/3] Execution plan..."
aforix batch plan -b "$BATCH_FILE"

echo
echo "[3/3] Running batch..."
aforix batch run -b "$BATCH_FILE"

echo
echo "==========================================================="
echo "Batch finished successfully."
echo "Check runs/batch for manifest.json."
echo "==========================================================="