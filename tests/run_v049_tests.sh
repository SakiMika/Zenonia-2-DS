#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
g++ -std=c++17 -Wall -Wextra -Itests/stubs tests/boot_wait_native_test.cpp -o "$tmp/boot"
"$tmp/boot"
python tests/boot_wait_arm_test.py
bash tests/run_v048_tests.sh
