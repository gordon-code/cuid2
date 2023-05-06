#!/bin/bash

set -e
set -x

REPO="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
REPO=$(dirname "$REPO../")
REPO=$(dirname "$REPO../")

ARG=$1

function auto_increment() {
    VERSION=$(python3 $REPO/ci/scripts/increment_version.py)
    sed "s/__version__ = .*/__version__ = '"$VERSION"'/g" -i $REPO/src/cuid2/__init__.py
}

function increment_manually() {
    echo $ARG
    VERSION=$ARG
    sed "s/__version__ = .*/__version__ = '"$VERSION"'/g" -i $REPO/src/cuid2/__init__.py
}


if [ $ARG = 'auto_increment' ]; then
    auto_increment
else
    increment_manually
fi

