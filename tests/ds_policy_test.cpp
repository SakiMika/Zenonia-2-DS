#include "zen_ds_policy.h"
#include "zen_render_fast.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <vector>
int main(){
 ZenDS::RepaintGate a;
 bool init=false,waiting=false;uint32_t last=0,wait=0;uint16_t keys=0;
 std::mt19937 rng(53);uint32_t time=0xffffff00,counter=0xfffffffc;
 for(int i=0;i<5000;++i){
  time+=rng()%35;counter+=rng()%3;uint16_t k=(rng()%8)?0x3ff:0x3fe;bool log=rng()%100==0;
  bool want=!init||log||k!=keys||uint32_t(counter-last)>=2;
  if(!want){if(!waiting){waiting=true;wait=time;}else want=uint32_t(time-wait)>=50;}
  if(want){init=true;last=counter;waiting=false;keys=k;}
  assert(a.allow(time,counter,k,log)==want);
 }
 puts("PASS source repaint gate: 5000 model comparisons, timer/key/log/wrap semantics");
 ZenDS::MinimapCache m;
 assert(!m.reuse(0,1,2,3,4));m.begin(0xffffffd0,1,2,3,4);m.finish(123,true);
 assert(m.reuse(0x20,1,2,3,4));assert(!m.reuse(0x34,1,2,3,4));
 assert(!m.reuse(0x20,1,3,3,4));assert(!m.reuse(0x20,2,2,3,4));
 assert(!m.reuse(0x20,1,2,4,4));assert(m.generation==1&&m.result==123);
 m.finish(456,false);assert(!m.initialized&&m.generation==1);m.invalidate();
 ZenDS::PanelCache p;assert(p.refresh(true,false,true,1));assert(!p.refresh(true,false,true,1));assert(p.refresh(true,false,true,2));assert(p.refresh(true,false,false,2));assert(!p.refresh(true,false,false,2));assert(p.refresh(true,true,false,2));assert(p.refresh(true,false,false,2));assert(p.refresh(false,false,false,2));assert(p.refresh(true,false,true,2));
 puts("PASS source 100ms minimap cache, identity/geometry keys, validity and panel generation invalidation");
 assert(ZenDS::consoleMap(0x80,0x06204000)==0x0689c000);
 assert(ZenDS::consoleMap(0x81,0x0689c000)==0x06204000);
 assert(ZenDS::consoleMap(0x80,0x06208000)==0x06208000);
 assert(ZenDS::consoleMap(0x00,0x06204000)==0x06204000);
 for(int offset=0;offset<2;++offset)for(int n=0;n<257;++n){
  std::vector<uint16_t>b(300,0x1234);ZenRenderFast::fill16(b.data()+offset+2,n,0xabcd);
  for(int j=0;j<300;++j)assert(b[j]==((j>=offset+2&&j<offset+2+n)?0xabcd:0x1234));
 }
 puts("PASS console VRAM address policy; packed fill aligned/halfword-aligned, 0..256 lengths, guards");
}
