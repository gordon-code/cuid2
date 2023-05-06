#!/bin/bash

# set -e
# set -x

REPO="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
REPO=$(dirname "$REPO../")
REPO=$(dirname "$REPO../")

echo Running flake8
python3 -m flake8 $REPO/src/cuid2 --config $REPO/ci/config/.flake8rc || true
echo Running mypy
python3 -m mypy --config-file $REPO/ci/config/.mypyrc $REPO/src/cuid2 || true
echo Running pylint
python3 -m pylint --rcfile=$REPO/ci/config/.pylintrc $REPO/src/cuid2 || true
echo Running safety
python3 -m safety check --full-report