#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

# -c "$APPROOT"/resources/watch
nohup bash -c "transmission-daemon --log-debug -f -w \"$APPROOT\" -g \"$APPROOT\"/transmission_config 2>&1 &" && sleep 10
