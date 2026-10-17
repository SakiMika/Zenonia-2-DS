#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
for t in title_native scene_native dialogue_native layout_policy hud_native; do
 g++ -std=c++17 -Itests/stubs "tests/${t}_test.cpp" -o "$tmp/$t"
 "$tmp/$t"
done
for t in scene_arm dialogue_arm hud_arm hud_render_target hud_pixel_arm hud_pzx_parser_arm log_touch; do
 python "tests/${t}_test.py"
done
python tests/native_gui_arm_test.py zenonia2nds/com/GameUI.gui --trampoline
