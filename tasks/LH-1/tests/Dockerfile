# Self-contained science runtime for the FusionX stellarator tasks (Linux AMD64).
# Public base image only: the same python:3.12-slim-bookworm digest as the B01 task package.
# Every other input ships in build-inputs/ (see build-inputs/SOURCES.md).
# Same software versions as the 2026-11-02 r8 runtime: Python 3.12.14, OpenMPI 5.0.10,
# gfortran 15.3.0, VMEC2000/NEO (STELLOPT 780f5db), SIMPLE 9269e86, SIMSOPT 1.10.6, booz_xform 0.0.9.
FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS physics-runtime
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
# /opt/physics first, so its Python 3.12.14 shadows the base image's /usr/local/bin/python.
ENV PATH=/opt/physics/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin MAMBA_ROOT_PREFIX=/opt/mamba
# Package sources are tried in order; override at build time if one is unreachable.
ARG CONDA_CHANNEL_BASES="https://conda.anaconda.org/conda-forge https://mirror.nju.edu.cn/anaconda/cloud/conda-forge https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge"
ARG PIP_INDEXES="https://pypi.org/simple https://mirrors.aliyun.com/pypi/simple https://mirrors.ustc.edu.cn/pypi/simple https://pypi.tuna.tsinghua.edu.cn/simple"
COPY build-inputs/micromamba-2.10.0-0.tar.bz2 build-inputs/micromamba-sha256.txt build-inputs/conda-linux-64.lock build-inputs/install_conda.sh /opt/build-inputs/
RUN bash /opt/build-inputs/install_conda.sh /opt/build-inputs/conda-linux-64.lock /opt/physics "$CONDA_CHANNEL_BASES"
ENV CONDA_PREFIX=/opt/physics NETCDF_DIR=/opt/physics
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg CMAKE_BUILD_PARALLEL_LEVEL=4
COPY build-inputs/pip-constraints.txt build-inputs/install_pip.sh /opt/build-inputs/
RUN bash /opt/build-inputs/install_pip.sh /opt/build-inputs/pip-constraints.txt "$PIP_INDEXES"

# Vendored sources at pinned commits; checksums are enforced before unpacking.
WORKDIR /opt/sources
COPY build-inputs/sources/ /opt/build-inputs/sources/
COPY build-inputs/unpack_sources.sh build-inputs/make_research.inc /opt/build-inputs/
RUN bash /opt/build-inputs/unpack_sources.sh /opt/build-inputs/sources /opt/sources \
    && cp /opt/build-inputs/make_research.inc /opt/sources/STELLOPT/SHARE/make_research.inc \
    && rm -rf /opt/build-inputs/sources

# Use the existing NEO correction for negative rotational transform.
RUN sed -i 's|CEILING(ONE / acc_req / iota_bar_fp)|CEILING(ONE / acc_req / ABS(iota_bar_fp))|' \
      STELLOPT/NEO/Sources/flint_bo.f90 \
    && cd STELLOPT && export STELLOPT_PATH="$PWD" MACHINE=research MYHOME="$PWD/bin" \
    && mkdir -p bin && ./build_all -j4 LIBSTELL NEO \
    && ./build_all -o release -j1 VMEC2000 \
    && cp bin/xvmec2000 bin/xneo /opt/physics/bin/
RUN mkdir -p SIMPLE/thirdparty \
    && cp pyplot-fortran/src/pyplot_module.F90 SIMPLE/thirdparty/pyplot_module.F90 \
    && cmake -S SIMPLE -B simple-build -DCMAKE_BUILD_TYPE=Release \
       -DENABLE_PYTHON_INTERFACE=OFF -DSIMPLE_TESTING=OFF -DSIMPLE_ENABLE_PYTHON_TOOLS=OFF \
       -DSIMPLE_DETERMINISTIC_FP=ON -DLIBNEO_SOURCE_DIR=/opt/sources/libneo \
       -DFETCHCONTENT_FULLY_DISCONNECTED=ON \
       -DFETCHCONTENT_SOURCE_DIR_FORTNUM=/opt/sources/fortnum \
       -DFETCHCONTENT_SOURCE_DIR_FORTIO=/opt/sources/fortio \
       -DFETCHCONTENT_SOURCE_DIR_FORTPLOT=/opt/sources/fortplot \
       -DCMAKE_Fortran_COMPILER=gfortran -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ \
       -DCMAKE_PREFIX_PATH=/opt/physics \
    && cmake --build simple-build -j4 \
    && cp simple-build/simple.x /opt/physics/bin/simple.x

# Keep the build sources and licenses; remove supplied example equilibria and histories.
RUN rm -rf STELLOPT/BENCHMARKS SIMPLE/test SIMPLE/tests SIMPLE/examples simple-build /opt/mamba/pkgs
# Terminal tools the Harbor Terminus agent probes for (tmux -V, asciinema --version); preinstalled so no
# network is needed when the task container starts with network_mode = "no-network".
COPY build-inputs/install_tools.sh /opt/build-inputs/
ARG APT_MIRRORS="http://deb.debian.org https://mirrors.aliyun.com https://mirrors.ustc.edu.cn"
RUN bash /opt/build-inputs/install_tools.sh "$APT_MIRRORS" "$PIP_INDEXES"
# No LD_LIBRARY_PATH: the conda-built solvers and Python extensions resolve /opt/physics/lib via RPATH
# (verified with ldd), and exporting it globally makes system binaries such as Debian's tmux load
# conda's libtinfo and crash ("NCURSES6_TINFO_6.4.current not found").
# Plain shell and no entrypoint for derived images, like the python:3.12-slim base used by B01.
SHELL ["/bin/sh", "-c"]
ENTRYPOINT []
WORKDIR /app
CMD ["bash"]

FROM physics-runtime
USER root
RUN mkdir -p /app /logs/verifier && rm -f /opt/physics/lib/python3.12/site-packages/simsopt/configs/*.curves /opt/physics/lib/python3.12/site-packages/simsopt/configs/*.currents /opt/physics/lib/python3.12/site-packages/simsopt/configs/*.ma /opt/physics/lib/python3.12/site-packages/simsopt/configs/*.dat
COPY case.json evaluate.py evaluation_support.py input.vmec physics.py test.sh /tests/
WORKDIR /app
CMD ["bash"]
