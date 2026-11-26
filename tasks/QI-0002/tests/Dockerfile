FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl git openssh-client xz-utils build-essential && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/quantum/legacy && /opt/quantum/legacy/bin/pip install --no-cache-dir numpy==2.2.6 scipy==1.15.3 \
 && python -m venv /opt/quantum/modern && /opt/quantum/modern/bin/pip install --no-cache-dir numpy==2.3.5 scipy==1.17.1
WORKDIR /app

COPY . /tests/
ENV PATH="/opt/quantum/legacy/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
