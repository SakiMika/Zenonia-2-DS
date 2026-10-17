"""Host tests of exact production blit, conversion and minimap code (not FPS)."""
from pathlib import Path
import subprocess, tempfile
r=Path(__file__).resolve().parents[1]
s=(r/'source/wipi_shim.cpp').read_text()
def func(marker):
 a=s.index(marker);b=s.index('{',a);depth=1;p=b+1
 while depth:
  if s[p]=='{':depth+=1
  elif s[p]=='}':depth-=1
  p+=1
 return s[a:p]
code=r'''
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cassert>
#include <cstdio>
#include <vector>
#include <random>
#include "zen_render_fast.h"
#include "zen_map_ui.h"
#include "map_reference.h"
struct WipiFramebuffer { uint32_t width,height,bpl,bpp;uint16_t *buf; };
struct WipiGraphicsContext { int clip_x1,clip_y1,clip_x2,clip_y2,offset_x,offset_y; };
uint16_t *fb_pixels16(WipiFramebuffer *fb){return fb?fb->buf:nullptr;}
'''+func('static void gfx_blit_fb(')+r'''
static uint16_t color(uint16_t p){return 0x8000 | (p>>11) | (((p>>6)&31)<<5) | ((p&31)<<10);}
int main(){
 alignas(32) uint16_t in[65536],out[65538];
 for(int i=0;i<65536;i++)in[i]=(uint16_t)i;
 out[65536]=out[65537]=0x1234;
 ZenRenderFast::convert565(out,in,65536);
 for(int i=0;i<65536;i++)assert(out[i]==color(in[i]));
 assert(out[65536]==0x1234 && out[65537]==0x1234);
 // Every color also occurs in the high halfword; check odd tail and guards.
 for(int i=0;i<65536;i++)in[i]=(uint16_t)(65535-i);
 const uint16_t tail_guard=out[65535];
 ZenRenderFast::convert565(out,in,65535);
 for(int i=0;i<65535;i++)assert(out[i]==color(in[i]));
 assert(out[65535]==tail_guard && out[65536]==0x1234);
 puts("PASS RGB565 conversion: all 65536 colors, both halfwords, odd tail, guards");
 std::mt19937 gen(53);
 auto rnd=[&](int n){return (int)(gen()%n);};
 for(int test=0;test<40000;++test){
  const int sw=1+rnd(35),sh=1+rnd(30),dw=1+rnd(35),dh=1+rnd(30);
  const int ss=sw+rnd(5),ds=dw+rnd(5);
  std::vector<uint16_t> src(ss*sh+16),dst(ds*dh+16),ref;
  for(auto &p:src)p=(uint16_t)gen();for(auto &p:dst)p=(uint16_t)gen();
  bool alias=test%3==0;
  // Same underlying buffer, also test descriptors with differing strides.
  if(alias){src.resize(2048);dst=src;}
  auto snapshot=alias?dst:src;ref=dst;
  WipiFramebuffer a{(unsigned)dw,(unsigned)dh,(unsigned)ds*2,16,dst.data()};
  WipiFramebuffer b{(unsigned)sw,(unsigned)sh,(unsigned)ss*2,16,alias?dst.data():src.data()};
  WipiGraphicsContext c{rnd(12)-4,rnd(12)-4,rnd(45)-3,rnd(40)-3,rnd(11)-5,rnd(11)-5};
  int dx=rnd(55)-20,dy=rnd(50)-20,sx=rnd(55)-20,sy=rnd(50)-20,w=rnd(60),h=rnd(50);
  for(int y=0;y<h;y++)for(int x=0;x<w;x++){
   int ix=sx+x,iy=sy+y,ox=dx+c.offset_x+x,oy=dy+c.offset_y+y;
   if(ix<0||iy<0||ix>=sw||iy>=sh||ox<0||oy<0||ox>=dw||oy>=dh)continue;
   if(ox<c.clip_x1||ox>c.clip_x2||oy<c.clip_y1||oy>c.clip_y2)continue;
   ref[oy*ds+ox]=snapshot[iy*ss+ix];
  }
  gfx_blit_fb(&a,dx,dy,w,h,&b,sx,sy,&c);assert(dst==ref);
 }
 puts("PASS 40000 randomized blits: clipping/offset/strides/overlap/guards match snapshot reference");
 std::vector<uint16_t> capture(256*192),actual(256*192+2),expected(256*192+2);
 for(auto &p:capture)p=(uint16_t)gen();
 for(int w=1;w<=92;w++)for(int h=1;h<=75;h++)for(bool valid:{false,true}){
  std::fill(actual.begin(),actual.end(),0x1234);expected=actual;
  ZenMapUI::draw(actual.data()+1,capture.data(),w,h,valid);
  ReferenceMapUI::draw(expected.data()+1,capture.data(),w,h,valid);
  assert(actual==expected);assert(actual.front()==0x1234 && actual.back()==0x1234);
 }
 puts("PASS minimap: 6900 sizes, valid/invalid states, bit-exact against v052, guards intact");
}
'''
# Frozen pre-optimization map renderer for pixel-for-pixel comparison.
with tempfile.TemporaryDirectory() as d:
 d=Path(d)
 (d/'test.cpp').write_text(code)
 subprocess.run(['g++','-O2','-std=c++17','-fno-strict-aliasing','-I'+str(r/'source'),'-I'+str(r/'tests'),str(d/'test.cpp'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
# Callback cache mode changes only redundant maintenance, not import binding.
for marker in ['static void process_timers(', 'static void media_notify(']:
 text=func(marker)
 assert '#if ZEN_CONSERVATIVE_CALLBACK_CACHE\n' in text
 assert 'DC_FlushAll(); IC_InvalidateAll();\n#endif' in text
assert 'DC_FlushRange(c,5*sizeof(uint32_t))' in s
m=(r/'source/main.cpp').read_text()
assert m.index('prepatch_lgt_imports(&image)')<m.index('entry(&p1,&p2,0)')
assert 'GUEST_TIME_NUM=6' in s and 'GUEST_TIME_DEN=5' in s
print('PASS cache-mode guards, code-write synchronization, eager import binding and guest speed retained')
