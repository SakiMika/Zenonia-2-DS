#pragma once
#include <stdint.h>
namespace ZenDS {
// Equivalent to the user-tested TEST3 repaint gate. Timers/audio are not gated.
struct RepaintGate {
 bool initialized=false,waiting=false;
 uint32_t counter=0,wait_ms=0;uint16_t keys=0;
 bool allow(uint32_t now,uint32_t fired,uint16_t current_keys,bool log) {
  bool draw=!initialized || log || current_keys!=keys || uint32_t(fired-counter)>=2;
  if(!draw) {
   if(!waiting){waiting=true;wait_ms=now;}
   else draw=uint32_t(now-wait_ms)>=50;
  }
  if(draw){initialized=true;counter=fired;waiting=false;keys=current_keys;}
  return draw;
 }
};
struct MinimapCache {
 bool initialized=false;
 uint32_t self=0,map=0,width=0,height=0,stamp=0,result=0,generation=0;
 bool reuse(uint32_t now,uint32_t object,uint32_t id,uint32_t w,uint32_t h) const {
  return initialized && self==object && map==id && width==w && height==h && uint32_t(now-stamp)<100;
 }
 void begin(uint32_t now,uint32_t object,uint32_t id,uint32_t w,uint32_t h) {
  self=object;map=id;width=w;height=h;stamp=now;
 }
 void finish(uint32_t value,bool valid){result=value;initialized=valid;if(valid)++generation;}
 void invalidate(){initialized=false;}
};
struct PanelCache {
 bool initialized=false,valid=false;uint32_t generation=0;
 void invalidate(){initialized=false;}
 bool refresh(bool bottom,bool log,bool current_valid,uint32_t gen) {
  if(log||!bottom){invalidate();return true;}
  if(initialized && valid==current_valid && generation==gen)return false;
  initialized=true;valid=current_valid;generation=gen;return true;
 }
};
// Console map base is 8*0x800 within H. CPU SUB_BG addresses must not be used
// while H is detached and C owns the 16-bit SUB bitmap.
constexpr uintptr_t ConsoleSubMap=0x06204000u;
constexpr uintptr_t ConsoleHiddenMap=0x0689c000u;
inline uintptr_t consoleMap(unsigned h_control,uintptr_t current) {
 if(current!=ConsoleSubMap && current!=ConsoleHiddenMap)return current;
 return (h_control&0x87u)==0x80u?ConsoleHiddenMap:
        (h_control&0x87u)==0x81u?ConsoleSubMap:current;
}
}
