#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python -I -B "$here/gold_a.py" "$@"
