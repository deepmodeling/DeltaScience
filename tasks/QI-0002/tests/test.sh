#!/bin/sh
set -eu
TEST_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SUBMISSION_DIR="${1:-${SUBMISSION_DIR:-/app/outputs}}"
RESULT_DIR="${2:-${RESULT_DIR:-${GRADER_LOG_DIR:-/logs/verifier}}}"
case "$SUBMISSION_DIR" in /*) ;; *) SUBMISSION_DIR="$PWD/$SUBMISSION_DIR" ;; esac
case "$RESULT_DIR" in /*) ;; *) RESULT_DIR="$PWD/$RESULT_DIR" ;; esac
export SUBMISSION_DIR RESULT_DIR PYTHONDONTWRITEBYTECODE=1
mkdir -p "$RESULT_DIR"
# A fresh attempt must never expose the previous attempt\'s reward on startup failure.
rm -f -- "$RESULT_DIR/reward.txt"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
exec /opt/quantum/legacy/bin/python -B "$TEST_DIR/grade.py" --submission "$SUBMISSION_DIR" --output "$RESULT_DIR/result.json"
