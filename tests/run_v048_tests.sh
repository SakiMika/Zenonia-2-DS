#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tests/resource_io_test.py
bash tests/run_v047_tests.sh
