#pragma once
#include <stdint.h>
struct ZenDecodedPcm { int16_t *pcm=nullptr; uint32_t samples=0,rate=0; };
// 1=loaded, 0=not the cached score, -1=cache unavailable/corrupt (use synth).
// On success the caller owns an aligned malloc-compatible PCM allocation.
int zen_load_title_pcm(const uint8_t *encoded,uint32_t size,ZenDecodedPcm *out);
