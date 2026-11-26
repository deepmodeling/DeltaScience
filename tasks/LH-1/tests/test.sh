#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python /tests/evaluate.py --case /tests/case.json --submission /app/boundary.json --output /logs/verifier
