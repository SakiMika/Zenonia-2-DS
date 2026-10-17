#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tests/copyright_position_arm_test.py
bash tests/run_v051_tests.sh
