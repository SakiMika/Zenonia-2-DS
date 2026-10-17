#pragma once
#include "lgt_loader.h"
// Stage 1: one known game profile. Unknown packages are rejected by the host
// packer. The core ELF entry/import/event loop remains outside this adapter.
bool runner_game_profile_install(LgtLoadedImage *image);
