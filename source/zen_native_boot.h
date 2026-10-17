#pragma once
#include "lgt_loader.h"
// Rating fade becomes fully opaque at counter16. Retain that frame;
// transition on update17 instead of51. No global timer/animation speed change.
constexpr uint16_t ZEN_RATING_LAST_TICK=16;
bool zen_native_boot_install(LgtLoadedImage *image);
