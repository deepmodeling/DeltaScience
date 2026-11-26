#!/bin/bash
set -eu
TEST_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
RESULT_DIR="${TF_GRADER_RESULT_DIR:-/logs/verifier}"
SUBMISSION="${TF_SUBMISSION_OUTPUT_DIR:-/root/outputs}/submission/flux.npz"
mkdir -p "$RESULT_DIR" /tmp/tf-mastu-mpl
rm -f "$RESULT_DIR/result.json" "$RESULT_DIR/reward.txt"
trap 'if [ ! -s "$RESULT_DIR/result.json" ]; then printf "{\"status\":\"platform_failure\",\"fault_layer\":\"grader_bootstrap\"}\n" > "$RESULT_DIR/result.json"; fi' EXIT
export MPLCONFIGDIR=/tmp/tf-mastu-mpl
PYTHONPATH="$TEST_DIR" /opt/challenge-runtime/mastu/bin/python -B "$TEST_DIR/grade.py" --submission "$SUBMISSION" --output "$RESULT_DIR"
