#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python3 tests/flashcard_structure_test.py
python3 tests/minimap_ds_runtime_test.py
g++ -std=c++17 -O2 -Wall -Wextra -Isource tests/flashcard_assets_test.cpp source/embedded_assets.cpp source/zen_predecoded_audio.cpp -o "$tmp/assets"
"$tmp/assets"
g++ -std=c++17 -fsyntax-only -Itests/stubs -Isource source/runner_game_profile.cpp source/embedded_assets.cpp source/zen_predecoded_audio.cpp
g++ -O2 -std=c++17 -fno-strict-aliasing -Isource tests/ds_policy_test.cpp -o "$tmp/policy"
"$tmp/policy"
g++ -O2 -std=c++17 -fno-strict-aliasing -Isource tests/map_ui_test.cpp -o "$tmp/map"
"$tmp/map"
g++ -O2 -std=c++17 -fno-strict-aliasing -Itests/stubs -Isource tests/minimap_native_test.cpp -o "$tmp/minimap"
"$tmp/minimap"
python3 tests/callback_cache_v053_test.py
python3 tests/performance_v053_test.py
