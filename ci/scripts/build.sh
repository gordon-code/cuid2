#!/bin/bash

set -e
set -x

REPO="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
REPO=$(dirname "$REPO../")
REPO=$(dirname "$REPO../")

cd $REPO
sudo python3 -m build
sudo python3 -m twine check $REPO/dist/*
sudo python3 -m pip install --force-reinstall $REPO/dist/*.whl