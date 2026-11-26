#!/usr/bin/env bash
# Verify and unpack the vendored source archives into the layout the build steps expect.
set -euo pipefail
src="$1"; dst="$2"
cd "$src"
sha256sum -c sources-sha256.txt
mkdir -p "$dst"
unpack() {
  mkdir -p "$dst/$2"
  tar -xzf "$src/$1" -C "$dst/$2" --strip-components=1
}
unpack STELLOPT-780f5db557ea.tar.gz STELLOPT
unpack SIMPLE-9269e8614e58.tar.gz SIMPLE
unpack libneo-f1bef44e80c4.tar.gz libneo
unpack fortnum-b382eff4d257.tar.gz fortnum
unpack fortio-11afd0bd1af0.tar.gz fortio
unpack fortplot-feabb592faf3.tar.gz fortplot
unpack pyplot-fortran-217d0c97a128.tar.gz pyplot-fortran
ls "$dst"
