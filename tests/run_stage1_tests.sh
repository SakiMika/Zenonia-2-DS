#!/usr/bin/env bash
# Compatibility entry point: Stage 2 external-folder runner.
set -euo pipefail
exec bash "$(dirname "$0")/run_flashcard_tests.sh" "$@"
