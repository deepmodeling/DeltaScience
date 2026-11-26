#!/usr/bin/env bash
# Preinstall the terminal tools the Harbor Terminus agent needs (tmux, asciinema), trying each
# Debian archive mirror and each PyPI index in turn, so the platform never has to install them.
set -euo pipefail
apt_mirrors="$1"; pip_indexes="$2"
src=/etc/apt/sources.list.d/debian.sources
export DEBIAN_FRONTEND=noninteractive
cp "$src" /tmp/debian.sources.orig
ok=0
for mirror in $apt_mirrors; do
  echo "==> apt from ${mirror}"
  sed -E "s|https?://deb\.debian\.org|${mirror%/}|g" /tmp/debian.sources.orig > "$src"
  if apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 \
     && apt-get install -y --no-install-recommends tmux; then ok=1; break; fi
  echo "==> ${mirror} failed; trying the next mirror" >&2
done
cp /tmp/debian.sources.orig "$src"
rm -rf /var/lib/apt/lists/*
[[ $ok == 1 ]] || { echo "tmux could not be installed from any mirror" >&2; exit 1; }
tmux -V
ok=0
for index in $pip_indexes; do
  echo "==> asciinema from ${index}"
  if python -m pip install --no-cache-dir --index-url "$index" --timeout 120 --retries 5 asciinema==2.4.0; then ok=1; break; fi
  echo "==> ${index} failed; trying the next index" >&2
done
[[ $ok == 1 ]] || { echo "asciinema could not be installed from any index" >&2; exit 1; }
asciinema --version
