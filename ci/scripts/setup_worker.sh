#!/bin/bash

set -e
set -x

REPO="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
REPO=$(dirname "$REPO../")
REPO=$(dirname "$REPO../")

# this hangs the worker at the update stage, so remove it and speed up builds!
sudo apt-get purge snap firefox

sudo apt-get update && sudo apt-get upgrade -y
python3 -m pip install --upgrade pip
python3 -m pip install -r $REPO/ci/config/requirements.txt
sudo python3 -m pip install --upgrade pip
sudo python3 -m pip install -r $REPO/ci/config/requirements.txt
