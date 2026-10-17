#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
g++ -std=c++17 -Wall -Wextra tests/boot_profile_test.cpp -o "$tmp/profile"
"$tmp/profile"
g++ -std=c++17 -Wall -Wextra -Itests/stubs tests/boot_hook_test.cpp -o "$tmp/hooks"
"$tmp/hooks"
bash tests/run_v049_tests.sh
