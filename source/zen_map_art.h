// Source-only distribution: neutral UI, no game-derived bitmap data.
#pragma once
#include <stdint.h>
#include <array>
static constexpr auto place_bar=[]() constexpr {
    std::array<uint16_t,234*22> p{};
    for(unsigned y=0;y<22;++y) for(unsigned x=0;x<234;++x)
        p[y*234+x]=(y==0 || y==21)?0xb14cu:0x9022u;
    return p;
}();
static constexpr std::array<uint16_t,35*29> map_logo{};
