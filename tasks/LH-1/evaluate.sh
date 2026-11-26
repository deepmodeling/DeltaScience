#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
submission="$(realpath "${1:?Usage: bash evaluate.sh boundary.json}")"
mkdir -p "$root/work"
output="$(mktemp -d "$root/work/evaluation-XXXXXX")"
docker run --rm --network none --platform linux/amd64 \
  --cpus 24 --memory 65536m \
  --mount "type=bind,src=$submission,dst=/app/boundary.json,readonly" \
  --mount "type=bind,src=$output,dst=/logs/verifier" \
  fusionx-task-precise-qa-verifier:2026.11.05-v4 bash /tests/test.sh
printf 'Results: %s\n' "$output"
