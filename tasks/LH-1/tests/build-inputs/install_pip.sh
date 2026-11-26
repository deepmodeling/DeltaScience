#!/usr/bin/env bash
# Install the pinned Python stack into /opt/physics, trying each PyPI index in turn.
set -euo pipefail
constraints="$1"; indexes="$2"
wheels=(numpy==2.2.6 scipy==1.15.3 simsopt==1.10.6 jax==0.11.2 jaxlib==0.11.2
        pybind11==2.13.6 ninja==1.13.2 meson==1.12.1 meson-python==0.22.1 wheel setuptools)
for index in $indexes; do
  echo "==> pip install from ${index}"
  if python -m pip install --no-cache-dir --only-binary=:all: --index-url "$index" \
        --timeout 120 --retries 5 -c "$constraints" "${wheels[@]}" \
     && python -m pip install --no-cache-dir --no-build-isolation --index-url "$index" \
        --timeout 120 --retries 5 -c "$constraints" booz-xform==0.0.9; then
    echo "==> Python stack ready from ${index}"
    exit 0
  fi
  echo "==> ${index} failed; trying the next index" >&2
done
echo "All PyPI indexes failed" >&2
exit 1
