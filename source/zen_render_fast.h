#pragma once
#include <stdint.h>
#include <stddef.h>
namespace ZenRenderFast {
inline void fill16(uint16_t *dst,size_t pixels,uint16_t color) {
    if(!dst)return;
    if((uintptr_t(dst)&3u) && pixels){*dst++=color;--pixels;}
    volatile uint32_t *out=reinterpret_cast<volatile uint32_t*>(dst);
    const uint32_t pair=uint32_t(color)|(uint32_t(color)<<16);
    while(pixels>=16){
        out[0]=pair;out[1]=pair;out[2]=pair;out[3]=pair;
        out[4]=pair;out[5]=pair;out[6]=pair;out[7]=pair;
        out+=8;pixels-=16;
    }
    while(pixels>=2){*out++=pair;pixels-=2;}
    if(pixels)*reinterpret_cast<volatile uint16_t*>(out)=color;
}

// DS ARM9 is little-endian. Source and destination must be 32-bit aligned;
// both the memalign(32) guest framebuffer and BG VRAM satisfy this contract.
// This is RGB565 -> opaque BGR555, with the same green-bit truncation as v052.
inline void convert565(uint16_t *dst,const uint16_t *src,size_t pixels) {
    auto *out=reinterpret_cast<volatile uint32_t*>(dst);
    auto *in=reinterpret_cast<const uint32_t*>(src);
    for(size_t i=0;i<pixels/2;++i) {
        const uint32_t p=in[i];
        out[i]=0x80008000u | ((p&0xf800f800u)>>11)
              | ((p&0x07c007c0u)>>1) | ((p&0x001f001fu)<<10);
    }
    if(pixels&1u) {
        const uint16_t p=src[pixels-1];
        reinterpret_cast<volatile uint16_t*>(dst)[pixels-1]=
            (uint16_t)(0x8000u | (p>>11) | ((p&0x07c0u)>>1) | ((p&31u)<<10));
    }
}
}
