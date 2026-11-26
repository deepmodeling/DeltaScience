#!/bin/bash
set -uo pipefail
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
mkdir -p /logs/verifier
chmod 700 /logs/verifier
# Harbor must always receive one finite scalar even if Python cannot import or
# start.  A successful verifier atomically replaces this transport fallback.
printf '0\n' > /logs/verifier/reward.txt
python3 "$script_dir/check_run.py"
if ! grep -Eq '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' /logs/verifier/reward.txt; then
  printf '0\n' > /logs/verifier/reward.txt
fi
cat /logs/verifier/reward.txt
exit 0
