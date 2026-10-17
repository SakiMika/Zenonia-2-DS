#include "hud_backend_stub.h"
// Host-side installer/wrapper regression test. Run with:
// g++ -std=c++17 -Itests/stubs tests/title_native_test.cpp -o /tmp/title-test
#include "../source/zen_native_layout.cpp"
#include <sys/mman.h>
#include <assert.h>
#include <array>
static std::array<uint32_t,6> captured;
static uint32_t capture_gui(uint32_t a,int x,int y,int group,uint32_t b,uint32_t c) {
    captured={a,(uint32_t)x,(uint32_t)y,(uint32_t)group,b,c};return 0x66bb;
}
static uint32_t capture(uint32_t a,int x,int y,uint32_t m,uint32_t b,uint32_t c) {
    captured={a,(uint32_t)x,(uint32_t)y,m,b,c};return 0x55aa;
}
void *lgt_translate_ptr(const LgtLoadedImage *im,uint32_t a) {
    return a>=im->text_old && a-im->text_old<im->text_size ? im->text+a-im->text_old:nullptr;
}
int main() {
    original_title_draw=capture;
    for(int y:{0,192,264,265,319}) {
        assert(zen_title_animation_draw(0x1234,64,y,7,11,13)==0x55aa);
        assert((captured==std::array<uint32_t,6>{0x1234,72,(uint32_t)(y-64),7,11,13}));
    }
    original_title_gui_draw=capture_gui;
    for(int group:{-1,1,2,3,4}) {
        assert(zen_title_gui_draw(0x4321,0,0,group,1,0)==0x66bb);
        assert((captured==std::array<uint32_t,6>{0x4321,8,(uint32_t)-96,(uint32_t)group,1,0}));
    }
    // No accumulated shift: wrappers transform call coordinates only.
    static_assert(ZenNativeLayout::TitleShiftX==8,"title center");
    for(int x:{-240,-1,0,64,120,239}) {
        for(int i=0;i<100;i++) {
            zen_title_animation_draw(0x1234,x,64,7,11,13);
            assert(captured[1]==(uint32_t)(x+8) && captured[2]==0);
            zen_title_gui_draw(0x4321,x,96,2,1,0);
            assert(captured[1]==(uint32_t)(x+8) && captured[2]==0);
        }
    }
    LgtLoadedImage im={};im.text_old=0x1000;im.text_size=0x8b538;
    im.data_old=0x1400000;im.data_size=0xf1c;
    im.text=(uint8_t*)mmap(nullptr,0x90000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_32BIT,-1,0);
    assert(im.text!=MAP_FAILED);
    auto at=[&](uint32_t a){return (uint8_t*)lgt_translate_ptr(&im,a);};
    const uint8_t prologue[8]={0x70,0xb5,0x81,0xb0,0x08,0x1c,0x1b,0x4b};
    memcpy(at(0x17a68),prologue,8);
    *(uint32_t*)at(0x17adc)=0x12345679;
    const uint32_t draw=(uint32_t)(uintptr_t)at(0x70e84)|1;
    *(uint32_t*)at(0x5a908)=draw;*(uint32_t*)at(0x5b3ec)=draw;
    *(uint16_t*)at(0x5aa3e)=0x1040;
    const uint32_t gui_draw=(uint32_t)(uintptr_t)at(0x17250)|1;
    *(uint32_t*)at(0x5a030)=gui_draw;*(uint32_t*)at(0x5b534)=gui_draw;
    *(uint16_t*)at(0x5b476)=0x3b0a;
    *(uint16_t*)at(0x5aab0)=0x33aa;
    for(auto pair:{std::array<uint32_t,2>{0x887f8,0x69ecc},
                   std::array<uint32_t,2>{0x88800,0x69f2c},
                   std::array<uint32_t,2>{0x88818,0x6af60}})
        *(uint32_t*)at(pair[0])=(uint32_t)(uintptr_t)at(pair[1])|1;
    const uint8_t dialogue[8]={0x70,0xb5,0x10,0x4c,0x82,0xb0,0x06,0x1c};
    memcpy(at(0x1c07c),dialogue,8);
    *(uint32_t*)at(0x1c0c0)=0x020eabcd;
    *(uint32_t*)at(0x1c660)=gui_draw;
    const uint8_t hud[8]={0xf0,0xb5,0x3e,0x4c,0x8d,0xb0,0x01,0x21};
    const uint8_t tail[8]={0xf0,0xb5,0x38,0x4a,0x8e,0xb0,0x80,0x18};
    memcpy(at(0x2033c),hud,8);memcpy(at(0x1e9f4),tail,8);
    *(uint32_t*)at(0x20438)=0x020ff004;
    *(uint32_t*)at(0x1ead8)=0x4fb;
    const uint8_t logo[8]={0x33,0x68,0x04,0x1c,0x1b,0x6a,0x30,0x1c};
    memcpy(at(0x5a744),logo,8);
    // Wrong binary/layout must fail without partially applying any patch.
    *(uint16_t*)at(0x5aab0)=0x33ab;
    assert(!zen_native_layout_install(&im));
    assert(!memcmp(at(0x17a68),prologue,8));assert(*(uint32_t*)at(0x5a908)==draw);
    *(uint16_t*)at(0x5aab0)=0x33aa;
    *(uint32_t*)at(0x5b3ec)=0;
    assert(!zen_native_layout_install(&im));
    assert(!memcmp(at(0x17a68),prologue,8));assert(*(uint16_t*)at(0x5aab0)==0x33aa);
    *(uint32_t*)at(0x5b3ec)=draw;
    // Body guard must also fail atomically, before hooks or prompt writes.
    *(uint16_t*)at(0x5aa3e)=0x1041;
    assert(!zen_native_layout_install(&im));
    assert(!memcmp(at(0x17a68),prologue,8));
    assert(*(uint16_t*)at(0x5aab0)==0x33aa);
    *(uint16_t*)at(0x5aa3e)=0x1040;
    for(uint32_t a:{0x5a030u,0x5b534u,0x5b476u,0x887f8u,0x88800u,0x88818u,0x1c07cu,0x1c660u,0x2033cu,0x1e9f4u,0x1ead8u}) {
        uint32_t saved=*(uint32_t*)at(a); *(uint32_t*)at(a)=0;
        assert(!zen_native_layout_install(&im));
        assert(!memcmp(at(0x17a68),prologue,8));
        assert(*(uint32_t*)at(0x5a908)==draw);
        *(uint32_t*)at(a)=saved;
    }
    assert(zen_native_layout_install(&im));
    assert(*(uint32_t*)at(0x5a030)==(uint32_t)(uintptr_t)&zen_title_gui_draw);
    assert(*(uint32_t*)at(0x5b534)==*(uint32_t*)at(0x5a030));
    assert(*(uint16_t*)at(0x5b476)==0x3b6a);
    assert(*(uint32_t*)at(0x887f8)==(uint32_t)(uintptr_t)&zen_scene_image);
    assert(*(uint32_t*)at(0x88800)==(uint32_t)(uintptr_t)&zen_scene_animation);
    assert(*(uint32_t*)at(0x88818)==(uint32_t)(uintptr_t)&zen_scene_text);
    assert(*(uint16_t*)at(0x5aa3e)==0x2004);
    assert(*(uint16_t*)((uint8_t*)loader_trampoline+40)==0x3c20);
    assert(*(uint16_t*)at(0x5aab0)==0x33a2);
    assert(*(uint32_t*)at(0x5a908)==(uint32_t)(uintptr_t)&zen_title_animation_draw);
    assert(*(uint32_t*)at(0x5b3ec)==*(uint32_t*)at(0x5a908));
    assert(*(uint16_t*)at(0x1c07c)==0x4b00);
    assert(*(uint32_t*)at(0x1c660)==(uint32_t)(uintptr_t)&zen_dialogue_gui_draw);
    assert(*(uint32_t*)((uint8_t*)loader_trampoline+80)==0x020eabcd);
    assert(*(uint32_t*)((uint8_t*)loader_trampoline+84)==((uint32_t)(uintptr_t)at(0x1c084)|1));
    assert(*(uint16_t*)at(0x2033c)==0x4b00);
    assert(*(uint16_t*)at(0x1e9f4)==0x4b00);
    assert(*(uint32_t*)((uint8_t*)loader_trampoline+112)==0x020ff004);
    assert(*(uint32_t*)((uint8_t*)loader_trampoline+144)==0x4fb);
    assert(*(uint32_t*)((uint8_t*)loader_trampoline+116)==((uint32_t)(uintptr_t)at(0x20344)|1));
    assert(*(uint32_t*)((uint8_t*)loader_trampoline+148)==((uint32_t)(uintptr_t)at(0x1e9fc)|1));
    assert(*(uint16_t*)at(0x17a68)==0x4b00);
    assert(*(uint16_t*)at(0x5a744)==0x4a00);
    puts("PASS: v041 atomic installer guards including both HUD entries and constant; prior hooks preserved; v037 title/menu wrappers preserved");
}
