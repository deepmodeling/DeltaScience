FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl git openssh-client xz-utils build-essential && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/challenge-runtime/mastu && /opt/challenge-runtime/mastu/bin/pip install --no-cache-dir freegs4e==0.15.0 shapely==2.2.0 numpy==2.3.5 numba==0.65.0 llvmlite==0.47.0 h5py==3.16.0 contourpy==1.3.3 matplotlib==3.10.8 python-dateutil==2.9.0.post0 six==1.17.0 pyparsing==3.3.2 pillow==12.2.0 packaging==26.0 kiwisolver==1.5.0 fonttools==4.62.1 cycler==0.12.1 scipy==1.17.1
WORKDIR /root

COPY . /tests/
ENV PATH="/opt/challenge-runtime/mastu/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
