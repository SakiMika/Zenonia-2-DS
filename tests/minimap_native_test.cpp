#include <cassert>
#include <sys/mman.h>
#include <vector>
#include "../source/zen_native_minimap.cpp"
static bool ready=true,moved=false,active=false,pixels=false,emit=true;
static int calls=0,texts=0,seenw=0,seenh=0;
// This legacy wrapper test deliberately bypasses cache; policy is tested separately.
void wipi_invalidate_minimap_cache(){}
bool wipi_try_cached_minimap(uint32_t,uint32_t,int,int,uint32_t*){return false;}
void wipi_store_minimap_cache(uint32_t){}
bool wipi_prepare_minimap(){return ready;}
bool wipi_begin_minimap(int w,int h){seenw=w;seenh=h;if(!moved)return false;active=true;pixels=false;return true;}
bool wipi_minimap_has_pixels(){return pixels;}
void wipi_end_minimap(){active=false;}
static uint32_t draw(uint32_t){calls++;pixels=active&&emit;return 0xbeef;}
static uint32_t table(uint32_t a,int b){assert(active&&a==0x02003000&&b==8);return 0x02004000;}
static const char *name(uint32_t a,int b,int c){assert(a==0x02004000&&b==0&&c==28);return (const char*)0x02005000;}
static uint32_t text(uint32_t a,const char*s,int x,int y,int color,int length,int flags){
 assert(active && a!=0x02006000 && x==0 && y==128 && color==0xffff && length==-1 && flags==-1 && !strcmp(s,"Ayles Town"));texts++;return 0;
}
void *lgt_translate_ptr(const LgtLoadedImage *im,uint32_t a){
 if(a>=im->text_old&&a-im->text_old<im->text_size)return im->text+a-im->text_old;
 if(a>=im->data_old&&a-im->data_old<im->data_size)return im->data+a-im->data_old;
 return nullptr;
}
int main(){
 assert(mmap((void*)0x02000000,0x100000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0)==(void*)0x02000000);
 uint32_t self=0x02001000;*(uint32_t*)(uintptr_t)(self+0xcc)=88;*(uint32_t*)(uintptr_t)(self+0xd0)=36;*(uint8_t*)(uintptr_t)(self+4)=28;
 manager_global=(uint32_t*)0x02002000;font_global=(uint32_t*)0x02002004;*manager_global=0x02003000;*font_global=0x02006000;strcpy((char*)0x02005000,"Ayles Town");
 *(uint32_t*)0x0200600c=1;*(uint32_t*)0x02006010=0x02007000;
 memset((void*)0x02007000,0x5a,0x6c);
 *(uint32_t*)0x0200700c=0x02008000;
 uint8_t font_snapshot[0x6c];memcpy(font_snapshot,(void*)0x02007000,0x6c);
 original=draw;table_get=table;name_get=name;text_draw=text;
 assert(zen_minimap_draw(self)==0xbeef&&calls==1&&texts==0&&!active);
 moved=true;assert(zen_minimap_draw(self)==0xbeef&&calls==2&&texts==1&&!active&&seenw==88&&seenh==36);
 assert(!memcmp(font_snapshot,(void*)0x02007000,0x6c));
 assert(*(uint32_t*)0x0200600c==1 && *(uint32_t*)0x02006010==0x02007000);
 emit=false;zen_minimap_draw(self);assert(texts==1&&!active);
 emit=true;
 for(int i=0;i<100;i++){
  moved=false;assert(zen_minimap_draw(self)==0xbeef && !active);
  moved=true;assert(zen_minimap_draw(self)==0xbeef && !active);
 }
 assert(texts==101);
 assert(!memcmp(font_snapshot,(void*)0x02007000,0x6c));
 // Missing font state: still capture the map; skip name safely.
 *(uint32_t*)0x02006010=0;zen_minimap_draw(self);assert(texts==101 && !active);
 original=nullptr;
 std::vector<uint8_t> code(0x8b538),data(0xf1c);
 LgtLoadedImage im{};im.text=code.data();im.text_old=0x1000;im.text_size=code.size();im.data=data.data();im.data_old=0x1400000;im.data_size=data.size();
 auto *entry=(uint8_t*)lgt_translate_ptr(&im,0x2f400);auto *lit=(uint32_t*)lgt_translate_ptr(&im,0x2f72c);
 const uint8_t bytes[]={0xf0,0xb5,0xca,0x4b,0x8d,0xb0,0x07,0x1c};memcpy(entry,bytes,8);*lit=(uint32_t)(uintptr_t)lgt_translate_ptr(&im,0x1214)|1u;
 entry[0]^=1;assert(!zen_native_minimap_install(&im));entry[0]^=1;
 ready=false;assert(!zen_native_minimap_install(&im)&&!memcmp(entry,bytes,8));
 ready=true;assert(zen_native_minimap_install(&im));assert(entry[0]==0 && entry[1]==0x4b);
 auto *tramp=(uint8_t*)((uintptr_t)original&~uintptr_t(1));uint32_t value;memcpy(&value,tramp+16,4);assert(value==*lit);memcpy(&value,tramp+20,4);assert(value==((uint32_t)(uintptr_t)(entry+8)|1u));
 puts("PASS native minimap wrapper: return/geometry/name/general-font/font-state-copy/early-return; guarded installer, allocation fallback, relocated literal/resume");
}
