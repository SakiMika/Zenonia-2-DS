#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tests/predecoded_audio_test.py
bash tests/run_v050_tests.sh
