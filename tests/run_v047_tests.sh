#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash tests/run_v046_tests.sh
python tests/title_center_arm_test.py
