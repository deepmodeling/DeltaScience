#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json /logs/verifier/score_breakdown.json /logs/verifier/continuous_score.json
set +e
/usr/local/bin/python -I -B /opt/retro-native/native_bridge.py relay
relay_exit=$?
set -e
exec /usr/local/bin/python -I -B /tests/continuous_scoring.py --relay-exit "$relay_exit"
