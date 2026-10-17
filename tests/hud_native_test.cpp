#include "hud_backend_stub.h"
#include "../source/zen_native_layout.cpp"
#include <sys/mman.h>
#include <cassert>
#include <initializer_list>
static void sprites(bool);
void *lgt_translate_ptr(const LgtLoadedImage*,uint32_t){return nullptr;}
static uint32_t context(){return 0x02001000;}
static bool early=false;
static int calls=0;
static int16_t *rect(unsigned i){return (int16_t*)(uintptr_t)(hud_items[i]+8);}
static uint32_t clock_draw(uint32_t s) {
    assert(s==123);assert(!test_hud_active && !hud_scope);
    assert(*(uint32_t*)0x02001040==7);
    for(unsigned i=0;i<11;i++)assert(rect(i)[1]==225);
    sprites(false);calls++;return 99;
}
static uint32_t draw(uint32_t s) {
    assert(s==123);assert(test_hud_active && hud_scope);
    assert(*(uint32_t*)0x02001040==7);
    for(unsigned i=0;i<11;i++) {
        assert(rect(i)[0]==95 && rect(i)[1]==161 && rect(i)[2]==98 && rect(i)[3]==4);
    }
    sprites(true);
    if(!early)assert(zen_native_hud_top_tail(s)==99);
    return 42;
}
static void sprites(bool shifted) {
 for(unsigned g: {1u,2u,3u,9u}) {
  unsigned n=g==1?4:g==2?11:1;
  uint32_t spr=0x02004000+g*0x300;
  assert(*(int16_t*)(uintptr_t)(spr+16)==(shifted?132:260));
  for(unsigned j=0;j<n;j++)
   assert(*(int16_t*)(uintptr_t)(spr+0x20+j*24+6)==(shifted?132:260));
 }
}
static uint32_t unshifted(uint32_t){assert(!test_hud_active);return 17;}
int main(){
 auto *m=mmap((void*)0x02000000,0x10000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
 assert(m==(void*)0x02000000);
 hud_gui=0x02003000;
 *(uint32_t*)0x0200300c=0x02003100;*(uint32_t*)0x0200310c=0x02003200;
 *(uint32_t*)0x02003208=0x02003300;*(uint32_t*)0x02003210=10;
 for(unsigned g: {1u,2u,3u,9u}) {
  unsigned n=g==1?4:g==2?11:1;uint32_t spr=0x02004000+g*0x300;
  *(uint32_t*)(uintptr_t)(0x02003300+g*4)=spr;
  *(uint32_t*)(uintptr_t)(spr+8)=spr+0x20;
  *(uint8_t*)(uintptr_t)(spr+12)=n;
  *(int16_t*)(uintptr_t)(spr+16)=260;
  for(unsigned j=0;j<n;j++) *(int16_t*)(uintptr_t)(spr+0x20+j*24+6)=260;
 }
 hud_item_count=11;hud_context=context;original_hud=draw;original_hud_top_tail=clock_draw;
 *(uint32_t*)0x02001040=7;
 *(uint32_t*)0x02001140=11; // independent font metric remains 11
 for(unsigned i=0;i<11;i++) {
  hud_items[i]=0x02002000+32*i;int16_t a[4]={95,225,98,4};memcpy(rect(i),a,8);
 }
 for(int i=0;i<100;i++) {
  early=i%2;assert(zen_native_hud_draw(123)==42);
  assert(!hud_scope && !test_hud_active && *(uint32_t*)0x02001040==7);
  for(unsigned j=0;j<11;j++)assert(rect(j)[1]==225);
  assert(*(uint32_t*)0x02001140==11);
 }
 assert(calls==50);
 original_hud=unshifted;
 // Atomic validation: a malformed fragment must not move any earlier ones.
 *(int16_t*)(uintptr_t)(0x02004000+9*0x300+0x20+6)=100;
 assert(zen_native_hud_draw(123)==17);
 *(int16_t*)(uintptr_t)(0x02004000+9*0x300+0x20+6)=260;
 sprites(false);test_hud_available=false;
 assert(zen_native_hud_draw(123)==17);test_hud_available=true;
 hud_item_count=0;assert(zen_native_hud_draw(123)==17);
 puts("PASS native HUD C++ scopes: TOP geometry scope + separate GUI/sprite offsets, restore before clock, early-return, 100 repeats, backend/geometry failure; metric11 intact");
}
