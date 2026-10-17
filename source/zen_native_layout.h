#pragma once
#include "lgt_loader.h"
// Installs a guarded hook into the original Thumb GUI loader. No final-frame
// cropping or sprite/font scaling is performed here.
bool zen_native_layout_install(LgtLoadedImage *image);
