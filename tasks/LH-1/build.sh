#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Same two builds the platform runs.
docker build --platform linux/amd64 -t fusionx-task-precise-qa-agent:2026.11.05-v4    "$root/environment"
docker build --platform linux/amd64 -t fusionx-task-precise-qa-verifier:2026.11.05-v4 "$root/tests"
