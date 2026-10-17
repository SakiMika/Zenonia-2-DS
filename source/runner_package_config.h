#pragma once
// Runtime-only settings. Game files are never compiled into the NDS.
#define RUNNER_PROFILE_ID "zenonia2-lgt-known"
#define RUNNER_GAME_DIRECTORY "zenonia2nds"
#define RUNNER_SAVE_BASENAME "ZKR1.sav"

// Real-time minimap cache lifetime after each completed native draw.
// Game timers, input and audio retain their original rates.
#define RUNNER_DS_MINIMAP_INTERVAL_MS 250u
#define RUNNER_DSI_MINIMAP_INTERVAL_MS 100u
