#!/bin/bash

set -e
set -x

REPO="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
REPO=$(dirname "$REPO../")
REPO=$(dirname "$REPO../")

PY_IGNORE_IMPORTMISMATCH=1 python3 -m pytest $REPO/ci/tests --ignore=$REPO/ci/tests/suite -c $REPO/ci/config/.pytestrc -s -vv --cov=$REPO/src/cuid2/ --cov-config=$REPO/ci/config/.coveragerc --cov-report xml:$REPO/ci/tests/coverage.xml --junit-xml=$REPO/ci/tests/report.xml --full-trace --log-file=$REPO/ci/tests/pytest.log --doctest-modules $REPO/src/cuid2
