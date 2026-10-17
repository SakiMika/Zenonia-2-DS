#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash tests/run_v045_tests.sh
python tests/minimap_text_arm_test.py
