#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash tests/run_v042_tests.sh
python tests/keymap_test.py
