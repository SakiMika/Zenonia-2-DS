#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash tests/run_v044_tests.sh
TMP=$(mktemp -d);trap 'rm -rf "$TMP"' EXIT
g++ -std=c++17 -Wall -Wextra -no-pie -Itests/stubs tests/minimap_native_test.cpp -o "$TMP/native"
"$TMP/native"
g++ -std=c++17 -Wall -Wextra tests/map_ui_test.cpp -o "$TMP/ui"
"$TMP/ui"
python tests/minimap_trampoline_arm_test.py
python tools/scan_map_dimensions.py > "$TMP/maps.json"
cmp "$TMP/maps.json" tests/map_geometry_report.json
printf 'PASS 150 original map headers: widest88x36, tallest39x71; geometry report reproducible\n'
