# Vendored build inputs

Everything the Dockerfile needs beyond the public base image is in this directory, so the
build never touches a private registry and never runs `ADD <git url>`.

| File | Content |
|---|---|
| `micromamba-2.10.0-0.tar.bz2` | conda-forge `linux-64/micromamba-2.10.0-0.tar.bz2` (BSD-3-Clause), sha256 `9a97976244929bbae28fb1fae504e74a3e7e6d1932870e3a03321f01b7fbd07b` in `micromamba-sha256.txt`; `install_conda.sh` extracts `bin/micromamba` and uses it to create `/opt/physics` from the lock. No conda installer is downloaded. |
| `conda-linux-64.lock` | Explicit conda-forge package list (177 packages) exported from the 2026-11-02 r8 runtime; same versions as `conda create ... python=3.12.14 gfortran=15.3.0 openmpi=5.0.10 hdf5=2.2.0 netcdf-fortran=4.6.4 ...` |
| `pip-constraints.txt` | Transitive Python pins observed in that runtime |
| `make_research.inc` | STELLOPT machine file (identical to the heredoc in the original `runtime/Dockerfile`) |
| `install_conda.sh`, `install_pip.sh`, `install_tools.sh`, `unpack_sources.sh` | Build helpers with mirror fallback and checksum verification |
| `sources/*.tar.gz` | Source archives at the pinned commits, downloaded from `https://codeload.github.com/<owner>/<repo>/tar.gz/<commit>` on 2026-11-04 |

| Archive | Repository | Commit |
|---|---|---|
| `STELLOPT-780f5db557ea.tar.gz` | PrincetonUniversity/STELLOPT | 780f5db557eacc7ca1160f4ca5a10a80922e4f26 (BENCHMARKS/ removed, see below) |
| `SIMPLE-9269e8614e58.tar.gz` | itpplasma/SIMPLE | 9269e8614e581ede8768e0bccb003b52db87e3be |
| `libneo-f1bef44e80c4.tar.gz` | itpplasma/libneo | f1bef44e80c4508f04594d4d2ca120eaf17564f8 |
| `fortnum-b382eff4d257.tar.gz` | lazy-fortran/fortnum | b382eff4d2578570c05cdc0b8471e11ce61fb8bd |
| `fortio-11afd0bd1af0.tar.gz` | lazy-fortran/fortio | 11afd0bd1af0c99ea4e9a1c0df683dbdcc299b69 |
| `fortplot-feabb592faf3.tar.gz` | lazy-fortran/fortplot | feabb592faf39bac8167b9193413912f2bb8ca48 |
| `pyplot-fortran-217d0c97a128.tar.gz` | jacobwilliams/pyplot-fortran | 217d0c97a12812ff5c5aca00e5439237e866bc91 |

The STELLOPT archive has its `BENCHMARKS/` directory (98 MB of example equilibria, not used by the
build) removed before packaging; the original recipe deleted the same directory after compiling.
SHA-256 of the unmodified GitHub archive: `95d533ab310a0ab59f9411e20cb99ae07aed0145201646079d221814ebdb869d`.
`sources/sources-sha256.txt` lists the checksums that `unpack_sources.sh` enforces.
