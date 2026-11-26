#!/bin/bash
set -euo pipefail
exec python -I -B /solution/replay_gold.py "$@"
