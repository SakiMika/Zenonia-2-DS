#include "zen_native_minimap.h"
#include "wipi_shim.h"
#include <malloc.h>
#include <string.h>
#include <stdio.h>
namespace {
using Draw=uint32_t (*)(uint32_t);
using Table=uint32_t (*)(uint32_t,int);
using Name=const char *(*)(uint32_t,int,int);
// 5f108 is the general name/string renderer used by dialogue and menus.
// 5f578 is a numeric sprite formatter (clock/stats), NOT an alphabet font.
using Text=uint32_t (*)(uint32_t,const char*,int,int,int,int,int);
static Draw original=nullptr;
static Table table_get=nullptr;
static Name name_get=nullptr;
static Text text_draw=nullptr;
static uint32_t *manager_global=nullptr,*font_global=nullptr;
static bool ram(uint32_t p,unsigned n){return p>=0x02000000u && p<0x03000000u && n<=0x03000000u-p;}
static uint32_t word(uint32_t p){uint32_t v=0;if(ram(p,4))memcpy(&v,(void*)(uintptr_t)p,4);return v;}
extern "C" uint32_t zen_minimap_draw(uint32_t self){
 if(!ram(self,0xd4) || (self&3u)){wipi_invalidate_minimap_cache();return original(self);}
 const int w=(int)word(self+0xcc),h=(int)word(self+0xd0);
 const uint32_t map=*(const uint8_t*)(uintptr_t)(self+4);
 uint32_t cached=0;
 if(wipi_try_cached_minimap(self,map,w,h,&cached))return cached;
 if(!wipi_begin_minimap(w,h)){wipi_invalidate_minimap_cache();return original(self);}
 const uint32_t result=original(self);
 // Match the game's table lookup in 2f96c: map table8, column0, current map id.
 // String-renderer wrapper is 14000f0 (same root as native name labels).
 if(wipi_minimap_has_pixels() && manager_global && font_global &&
    ram(*manager_global,4) && ram(*font_global,4)){
  const uint32_t table=table_get(*manager_global,8);
  if(ram(table,4)){
   const unsigned id=*(const uint8_t*)(uintptr_t)(self+4);
   const char *name=name_get(table,0,id);
   const uint32_t p=(uint32_t)(uintptr_t)name;
   if(ram(p,1)){
    // Reject an unterminated pointer instead of letting the font walk memory.
    unsigned n=0;while(n<127 && ram(p+n,1) && name[n])n++;
    if(n && n<127){
     const uint32_t wrapper=*font_global;
     if(ram(wrapper,20)){
      // 5f108 chooses wrapper+10 when wrapper+c !=0, otherwise
      // wrapper+4 -> parent+3c. Validate that chain before calling it.
      const uint32_t parent=word(wrapper+4);
      const uint32_t font=word(wrapper+12)?word(wrapper+16):word(parent+0x3c);
      const uint32_t context=word(font+12);
      const int32_t offset=(int32_t)word(context+0x40);
      if(ram(font,0x6c) && ram(context,0x44) && offset>=-512 && offset<=512){
       // The general font updates pen/cached metrics. Use local copies so
       // this extra title draw cannot change subsequent gameplay text state.
       uint32_t saved_font[0x6c/4],saved_wrapper[5];
       memcpy(saved_font,(void*)(uintptr_t)font,sizeof(saved_font));
       memcpy(saved_wrapper,(void*)(uintptr_t)wrapper,sizeof(saved_wrapper));
       // Font constructor d9e4 clears exactly 0x6c bytes; +68 is
       // the optional text callback. Plain map labels must not invoke it.
       saved_font[0x68/4]=0;
       // dae8 adds context+40 to Y. Counter it so the title stays
       // in the scratch band, even when viewport offset is not zero.
       saved_font[0x38/4]=0;
       saved_font[0x3c/4]=(192u<<16)|256u;
       saved_font[0x44/4]=(uint32_t)(192-offset);
       saved_wrapper[3]=1;
       saved_wrapper[4]=(uint32_t)(uintptr_t)saved_font;
       text_draw((uint32_t)(uintptr_t)saved_wrapper,name,0,128-offset,0xffff,-1,-1);
      }
     }
    }
   }
  }
 }
 wipi_end_minimap();wipi_store_minimap_cache(result);return result;
}
}
bool zen_native_minimap_install(const LgtLoadedImage *img){
 if(original)return true;
 if(!img || img->text_old!=0x1000u || img->text_size!=0x8b538u || img->data_old!=0x1400000u || img->data_size!=0xf1cu)return false;
 uint8_t *entry=(uint8_t*)lgt_translate_ptr(img,0x2f400);
 uint32_t *context=(uint32_t*)lgt_translate_ptr(img,0x2f72c);
 const uint8_t expected[8]={0xf0,0xb5,0xca,0x4b,0x8d,0xb0,0x07,0x1c};
 const uint32_t want=(uint32_t)(uintptr_t)lgt_translate_ptr(img,0x1214)|1u;
 if(!entry || !context || memcmp(entry,expected,8) || *context!=want)return false;
 table_get=(Table)((uintptr_t)lgt_translate_ptr(img,0x1a3e8)|1u);
 name_get=(Name)((uintptr_t)lgt_translate_ptr(img,0x19d60)|1u);
 text_draw=(Text)((uintptr_t)lgt_translate_ptr(img,0x5f108)|1u);
 manager_global=(uint32_t*)lgt_translate_ptr(img,0x14000cc);
 font_global=(uint32_t*)lgt_translate_ptr(img,0x14000f0);
 if(!manager_global || !font_global)return false;
 uint8_t *tramp=(uint8_t*)memalign(32,32);
 if(!tramp)return false;
 if(!wipi_prepare_minimap()){free(tramp);return false;}
 // Relocate the displaced PC-relative LDR r3. r4 is callee-saved on the stack
 // and overwritten by the guest before use; it is safe as the resume scratch.
 const uint16_t code[8]={0xb5f0,0x4b03,0xb08d,0x1c07,0x4c02,0x4720,0x46c0,0x46c0};
 memcpy(tramp,code,16);memcpy(tramp+16,context,4);
 const uint32_t resume=(uint32_t)(uintptr_t)(entry+8)|1u;
 memcpy(tramp+20,&resume,4);
 original=(Draw)((uintptr_t)tramp|1u);
 DC_FlushRange(tramp,32);IC_InvalidateRange(tramp,32);
 const uint16_t veneer[2]={0x4b00,0x4718};const uint32_t hook=(uint32_t)(uintptr_t)&zen_minimap_draw;
 memcpy(entry,veneer,4);memcpy(entry+4,&hook,4);
 DC_FlushRange(entry,8);IC_InvalidateRange(entry,8);
 printf("[MAP046] SELECT: native minimap TOP <-> purple SUB; gear16x16\n");return true;
}
