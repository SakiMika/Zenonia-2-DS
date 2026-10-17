#include "hud_backend_stub.h"
#include "../source/zen_native_layout.cpp"
#include <sys/mman.h>
#include <cassert>
#include <array>
void *lgt_translate_ptr(const LgtLoadedImage*,uint32_t){return nullptr;}
static uint32_t capture_rect(uint32_t out,uint32_t g) {
    int16_t r[4]={1,(int16_t)(g==4?267:247),238,(int16_t)(g==4?53:19)};
    memcpy((void*)(uintptr_t)out,r,8);return out;
}
static std::array<uint32_t,6> seen;
static uint32_t capture_draw(uint32_t o,int x,int y,int g,uint32_t s,uint32_t z) {
    seen={o,(uint32_t)x,(uint32_t)y,(uint32_t)g,s,z};return 0x1234;
}
int main() {
    void *base=mmap((void*)0x02000000,4096,PROT_READ|PROT_WRITE,
        MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);assert(base==(void*)0x02000000);
    original_dialogue_rect=capture_rect;original_dialogue_gui=capture_draw;
    for(unsigned g=0;g<10;g++)for(unsigned repeat=0;repeat<100;repeat++) {
        assert(zen_dialogue_rect(0x02000000,g)==0x02000000);
        int16_t r[4];memcpy(r,base,8);
        assert(r[0]==1 && r[2]==238 && r[3]==(g==4?53:19));
        assert(r[1]==(g==4?267:247)-(g>=4&&g<=8?128:0));
        assert(zen_dialogue_gui_draw(0x1234,8,7,g,1,0)==0x1234);
        assert((seen==std::array<uint32_t,6>{0x1234,8,(uint32_t)(7-(g>=4&&g<=8?128:0)),g,1,0}));
    }
    // Body y139, baseline146; retain all 3 rows, 11px glyphs, fixture3px gap.
    for(int i=0;i<3;i++)assert(146+i*14+11<=192);
    puts("PASS dialogue wrappers: body/name groups4..8 move -128; size/X/flags/result intact; 100 repeats no accumulation; other groups untouched");
}
