#include "zen_native_boot.h"
#include "zen_boot_profile.h"
#include <stdio.h>
#include <string.h>

namespace {
using BootFn=uint32_t (*)(uint32_t);
static BootFn rating_update=nullptr,auth_update=nullptr,title_draw=nullptr;
static uint32_t traced_rating(uint32_t self) {
    uint32_t counter=0;
    const bool valid=!(self&3u) && self>=0x02000000u && self<=0x02ffffd4u;
    if(valid) memcpy(&counter,(void*)(uintptr_t)(self+0x28),4);
    ZenBootProfile::phase(3,counter);
    if(counter==ZEN_RATING_LAST_TICK && ZenBootProfile::trace.active &&
       !ZenBootProfile::trace.transition_at)
        ZenBootProfile::trace.transition_at=zen_boot_clock_ms();
    const uint32_t result=rating_update(self);
    if(valid && ZenBootProfile::trace.active) {
        uint32_t next=0;memcpy(&next,(void*)(uintptr_t)(self+8),4);
        if(next==4 && !ZenBootProfile::trace.rating_exit)
            ZenBootProfile::trace.rating_exit=zen_boot_clock_ms();
    }
    return result;
}
static uint32_t traced_auth(uint32_t self) {
    ZenBootProfile::phase(4);return auth_update(self);
}
static uint32_t traced_title(uint32_t self) {
    ZenBootProfile::phase(5);const uint32_t result=title_draw(self);
    if(ZenBootProfile::trace.active && !ZenBootProfile::trace.title_end)
        ZenBootProfile::trace.title_end=zen_boot_clock_ms();
    return result;
}
}

bool zen_native_boot_install(LgtLoadedImage *image) {
    if(!image || !image->text || image->text_old!=0x1000u ||
       image->text_size!=0x8b538u) return false;
    // Entire private state3 update, including its native call to state4 init.
    // Leave the other logo delay at5a144, certi init, title loading and all
    // shared timer functions intact. Never patch the on-disk binary.
    const uint8_t expected[]={0x00,0xb5,0x83,0x6a,0x01,0x33,0x83,0x62,
        0x32,0x2b,0x01,0xdd,0xff,0xf7,0x9a,0xff,0x00,0x20,0x02,0xbc,0x08,0x47};
    uint8_t *entry=(uint8_t*)lgt_translate_ptr(image,0x5a3fcu);
    if(!entry || memcmp(entry,expected,sizeof(expected))) return false;
    const uint32_t slots[]={0x87640u,0x87650u,0x87670u};
    const uint32_t targets[]={0x5a3fcu,0x5a4a8u,0x5a634u};
    uint32_t *pools[3]; uint32_t originals[3];
    for(unsigned i=0;i<3;++i) {
        pools[i]=(uint32_t*)lgt_translate_ptr(image,slots[i]);
        originals[i]=(uint32_t)(uintptr_t)lgt_translate_ptr(image,targets[i])|1u;
        if(!pools[i] || *pools[i]!=originals[i]) return false;
    }
    const uint16_t cmp_r3=(uint16_t)(0x2b00u|ZEN_RATING_LAST_TICK);
    memcpy(entry+8,&cmp_r3,2);
    DC_FlushRange(entry+8,2); IC_InvalidateRange(entry+8,2);
    rating_update=(BootFn)(uintptr_t)originals[0];
    auth_update=(BootFn)(uintptr_t)originals[1];
    title_draw=(BootFn)(uintptr_t)originals[2];
    const uint32_t hooks[]={(uint32_t)(uintptr_t)&traced_rating,
        (uint32_t)(uintptr_t)&traced_auth,(uint32_t)(uintptr_t)&traced_title};
    for(unsigned i=0;i<3;++i) {
        *pools[i]=hooks[i];DC_FlushRange(pools[i],4);IC_InvalidateRange(pools[i],4);
    }
    ZenBootProfile::trace.hooks=true;
    printf("[BOOT050] diagnostic phase hooks installed; v049 wait retained\n");
    return true;
}
