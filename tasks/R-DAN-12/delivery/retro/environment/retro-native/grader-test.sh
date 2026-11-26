#!/bin/bash
set -eu
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
if [ "$(id -u)" != 0 ]; then echo VERIFIER_USER_REQUIRED >&2; exit 71; fi
export RETRO_P_ENDPOINT=http://p-service:20765
export RETRO_SERVICE_BINDING_SOURCE=/run/retro-platform/service.json
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}p-service,localhost,127.0.0.1"
cd /tests
exec /usr/local/bin/python -I -B /opt/retro-native/grading_launcher.py "$@"
