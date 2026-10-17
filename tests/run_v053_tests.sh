#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tests/performance_v053_test.py
python tests/callback_cache_v053_test.py
bash tests/run_v052_tests.sh
