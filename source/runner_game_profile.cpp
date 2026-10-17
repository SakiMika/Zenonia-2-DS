#include "runner_game_profile.h"
#include "wipi_shim.h"
#include "zen_native_layout.h"
#include "zen_native_minimap.h"
#include "zen_native_boot.h"
#include <stdio.h>

typedef int (*Zen2SoundRequestFn)(void*,int,int,int);
static Zen2SoundRequestFn g_zen2_sound_request_orig=nullptr;

extern "C" int zen2_sound_request_hook(void *self,int id,int arg2,int flag) {
    wipi_note_sound_request(id,arg2,flag);
    if(!g_zen2_sound_request_orig) return 0;
    return g_zen2_sound_request_orig(self,id,arg2,flag);
}

static unsigned patch_zen2_sound_request(LgtLoadedImage *img) {
    if(!img || !img->text) return 0;
    // Zenonia 2 Thumb function 0x15301 formats sound/%03d.mmf and is the
    // central request method used by gameplay SFX/BGM. Relocations turn its
    // literal function pointers into the relocated runtime address; replace
    // those literals with our ARM hook while retaining the original target.
    const uint32_t old_entry=0x00015301u;
    void *translated=lgt_translate_ptr(img,old_entry);
    if(!translated) { printf("[SNDHOOK!] target missing\n"); return 0; }
    const uint32_t target=(uint32_t)(uintptr_t)translated;
    const uint32_t hook=(uint32_t)(uintptr_t)&zen2_sound_request_hook;
    g_zen2_sound_request_orig=(Zen2SoundRequestFn)(uintptr_t)target;
    unsigned patched=0;
    for(uint32_t off=0; off+4<=img->text_size; off+=4) {
        uint32_t *w=(uint32_t*)(img->text+off);
        if(*w==target) { *w=hook; patched++; }
    }
    if(patched) {
        DC_FlushRange(img->text,img->text_size);
        IC_InvalidateRange(img->text,img->text_size);
    }
    printf("[SNDHOOK] %08lx -> %08lx ptrs=%u\n",
           (unsigned long)target,(unsigned long)hook,patched);
    return patched;
}

bool runner_game_profile_install(LgtLoadedImage *image) {
    patch_zen2_sound_request(image);
    if(!zen_native_layout_install(image)) return false;
    if(!zen_native_minimap_install(image))
        printf("[MAP] profile hook unavailable; original minimap retained\n");
    if(!zen_native_boot_install(image))
        printf("[BOOT] phase hook unavailable; original wait retained\n");
    return true;
}
