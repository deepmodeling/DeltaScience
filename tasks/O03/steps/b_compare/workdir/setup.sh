#!/usr/bin/env bash
set -euo pipefail

key=.branch_key_ab
state=/opt/o03_branch_state/a_output.tar.enc
output_dir=${OUTPUT_DIR:-/workspace/output}
if [[ ! -s "$key" || ! -s "$state" ]]; then
  echo "Missing sealed A branch or comparison key" >&2
  exit 31
fi
tmp=$(python -c 'import tempfile; print(tempfile.mkdtemp(prefix="o03-ab-merge."))')
cleanup() {
  python - "$tmp" <<'PY'
import shutil, sys
shutil.rmtree(sys.argv[1], ignore_errors=True)
PY
}
trap cleanup EXIT
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -nosalt -pass "file:${key}" -in "$state" \
  | tar -xf - -C "$tmp"
python - <<'PY'
import pathlib, shutil
shutil.rmtree(pathlib.Path("/app/inputs"), ignore_errors=True)
PY
python /usr/local/bin/o03_merge_ab_outputs.py "$tmp" "$output_dir"
rm -f "$state" "$key" setup.sh
