#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$root/work"
docker run --rm -it --network none --platform linux/amd64 \
  --cpus 24 --memory 65536m \
  --mount "type=bind,src=$root/work,dst=/work" fusionx-task-precise-qa-agent:2026.11.05-v4 bash
