#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
g++ -O2 -std=c++17 -fno-strict-aliasing -Isource tests/ds_policy_test.cpp -o "$tmp/policy"
"$tmp/policy"
python3 tests/callback_cache_v053_test.py
python3 tests/performance_v053_test.py
g++ -O2 -std=c++17 -fno-strict-aliasing -Itests/stubs -Isource tests/minimap_native_test.cpp -o "$tmp/minimap"
"$tmp/minimap"
