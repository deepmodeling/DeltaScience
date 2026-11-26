#!/usr/bin/env bash
# Create /opt/physics from the explicit conda-forge lock using the vendored micromamba binary
# (no conda installer is downloaded), trying each channel base URL in turn.
set -euo pipefail
lock="$1"; prefix="$2"; bases="$3"
inputs="$(cd -- "$(dirname -- "$lock")" && pwd)"
if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "This lock is linux-64 only; build with --platform linux/amd64" >&2
  exit 1
fi
# micromamba 2.10.0 from conda-forge (BSD-3-Clause); checksum enforced before unpacking.
(cd "$inputs" && sha256sum -c micromamba-sha256.txt)
python3 - "$inputs/micromamba-2.10.0-0.tar.bz2" /usr/local/bin <<'PY'
import sys, tarfile
with tarfile.open(sys.argv[1]) as tar:
    member = tar.getmember("bin/micromamba")
    member.name = "micromamba"
    tar.extract(member, sys.argv[2], filter="data")
PY
chmod 0755 /usr/local/bin/micromamba
export MAMBA_ROOT_PREFIX="${MAMBA_ROOT_PREFIX:-/opt/mamba}"
mkdir -p "$MAMBA_ROOT_PREFIX"
printf 'remote_max_retries: 5\nremote_connect_timeout_secs: 30\n' > /root/.mambarc
micromamba --version
for base in $bases; do
  echo "==> micromamba create from ${base}"
  sed "s|https://conda.anaconda.org/conda-forge|${base}|" "$lock" > /tmp/conda-explicit.lock
  rm -rf "$prefix"
  if micromamba create -y -p "$prefix" -f /tmp/conda-explicit.lock; then
    rm -f /tmp/conda-explicit.lock
    micromamba clean -a -y
    echo "==> conda environment ready from ${base}"
    exit 0
  fi
  echo "==> ${base} failed; trying the next source" >&2
done
echo "All conda package sources failed" >&2
exit 1
