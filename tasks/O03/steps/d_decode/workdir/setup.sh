#!/usr/bin/env bash
set -euo pipefail

shopt -s nullglob
keys=(.payload_key_*)
if [[ ${#keys[@]} -ne 1 ]]; then
  echo "Expected exactly one stage payload key" >&2
  exit 20
fi
key=${keys[0]}
stage=${key#.payload_key_}
payload_dir=${O03_PAYLOAD_DIR:-/opt/o03_payloads}
app_dir=${O03_APP_DIR:-/app}
payload="${payload_dir}/${stage}.tar.enc"
manifest="${payload_dir}/payload_manifest.json"

python - "$stage" "$payload" "$manifest" <<'PY'
import hashlib, json, pathlib, sys
stage, payload_path, manifest_path = sys.argv[1:]
payload = pathlib.Path(payload_path)
row = json.loads(pathlib.Path(manifest_path).read_text(encoding="utf-8"))["payloads"][stage]
if payload.name != row["filename"] or payload.stat().st_size != row["size_bytes"]:
    raise SystemExit("payload identity mismatch")
h = hashlib.sha256()
with payload.open("rb") as handle:
    for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
        h.update(chunk)
if h.hexdigest().upper() != row["sha256"]:
    raise SystemExit("payload SHA-256 mismatch")
PY

tmp=$(python -c 'import tempfile; print(tempfile.mkdtemp(prefix="o03-stage."))')
cleanup() {
  python - "$tmp" <<'PY'
import shutil, sys
shutil.rmtree(sys.argv[1], ignore_errors=True)
PY
}
trap cleanup EXIT
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -nosalt -pass "file:${key}" -in "$payload" \
  | tar -xf - -C "$tmp"
python - "$tmp" "$app_dir" "$key" <<'PY'
import pathlib, shutil, sys
source, destination, key = sys.argv[1:]
shutil.rmtree(pathlib.Path(destination) / "inputs", ignore_errors=True)
shutil.copytree(source, destination, dirs_exist_ok=True)
pathlib.Path(key).unlink(missing_ok=True)
pathlib.Path("setup.sh").unlink(missing_ok=True)
PY
