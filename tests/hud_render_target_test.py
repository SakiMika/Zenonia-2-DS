"""Compile exact scoped-target/presenter/descriptor code extracted from wipi_shim.
Hardware, LOG drawing and callback setup are host stubs, not a full libnds build.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1];src=(root/'source/wipi_shim.cpp').read_text()
def function(marker):
 a=src.index(marker);b=src.index('{',a);depth=1;p=b+1
 while depth:
  if src[p]=='{':depth+=1
  elif src[p]=='}':depth-=1
  p+=1
 return src[a:p]+'\n'
assert 'QUICK_SLOT_' not in src
assert "const int key='4'+slot" not in src
present=function('void wipi_present(void)')
assert 'g_native_hud_fb' not in src
assert 'g_native_hud_alias' not in src
assert 'draw_log_button_to(subdst)' in present

code='''#include <stdint.h>
#include <malloc.h>
#include <cstring>
#include <cassert>
#include <cstdio>
#include <sys/mman.h>
constexpr int DS_W=256,DS_H=192,PHONE_W=256,PHONE_H=192;
struct WipiFramebuffer { uint32_t width,height,bpl,bpp,buf; };
struct WipiCletState { uint32_t callbacks[6];bool started; };
static WipiCletState g_clet{};
static bool g_in_paint=false,g_present_pending=false,g_log_visible=false;
static bool g_native_hud_active=false,g_sub_static_valid=false;
static uint16_t *g_phone_fb,*g_ds_fb,*g_sub_fb,*g_top_comp,*g_sub_comp;
static WipiFramebuffer g_screen_fb{},g_minimap_alias{};
static uint16_t *g_minimap_fb=nullptr;
static bool g_minimap_ready=false,g_minimap_bottom=false,g_minimap_capture=false,g_minimap_valid=false,g_repaint_pending=false;
static int g_minimap_w=0,g_minimap_h=0;
namespace ZenMapUI {void draw(uint16_t*,const uint16_t*,int,int,bool){}}

static int log_draws=0;
#define BIT(n) (1u<<(n))
#define RGB15(r,g,b) ((r)|((g)<<5)|((b)<<10))
void DC_FlushRange(const void*,unsigned){}
void draw_log_button_to(uint16_t*){log_draws++;}
void wipi_end_native_hud();
'''
code+='#include "'+str(root/'source/zen_render_fast.h')+'"\n'
code+='#include "'+str(root/'source/zen_boot_profile.h')+'"\nuint32_t zen_boot_clock_ms(void){return 0;}\n'
a=src.index('struct BootCostScope {');b=src.index('extern "C" int knl_get_resource_id(',a)
code+=src[a:b]
for marker in ['static bool valid_ptr(', 'static WipiFramebuffer *as_fb(',
               'static uint16_t *fb_pixels16(', 'extern "C" void *fb_ptr(',
               'bool wipi_prepare_minimap(', 'bool wipi_begin_minimap(', 'bool wipi_minimap_has_pixels(', 'void wipi_end_minimap(', 'void wipi_toggle_minimap(',
               'bool wipi_begin_native_hud(', 'void wipi_end_native_hud(',
               'static void paint_region(']:code+=function(marker)
# Color conversion is the source's existing formula, not new resampling.
a=src.index('uint16_t rgb565_to_ds15');a=src.rfind('\n',0,a)+1
code+=function(src[a:src.index('(',a)+1])+present
code+='''void paint_probe(int,int,int,int){
 assert(g_in_paint && !g_native_hud_active);
 assert(fb_ptr()==g_phone_fb);
}
int main(){
 void *base=mmap((void*)0x02000000,0x100000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
 assert(base==(void*)0x02000000);
 g_phone_fb=(uint16_t*)0x02010000;
 g_ds_fb=(uint16_t*)0x02050000;g_sub_fb=(uint16_t*)0x02070000;
 g_screen_fb={256,192,512,16,0x02010000};
 auto *cached=(WipiFramebuffer*)0x02001000;*cached=g_screen_fb;
 auto *image=(WipiFramebuffer*)0x02001040;*image=g_screen_fb;image->buf=0x02090000;
 for(int i=0;i<256*192;i++)g_phone_fb[i]=0xf800;
 for(int j=0;j<100;j++){
  assert(wipi_begin_native_hud());assert(!wipi_begin_native_hud());
  assert(g_screen_fb.buf==0x02010000 && fb_ptr()==g_phone_fb);
  assert(as_fb(0x02001000)==cached);
  assert(fb_pixels16(as_fb(0x02001000))==g_phone_fb);
  // Simulate a native HUD pixel in the final panel row: same TOP storage.
  fb_pixels16(as_fb(0x02001000))[191*256+239]=0x07e0;
  assert(as_fb(0x02001040)==image && image->buf==0x02090000);
  wipi_end_native_hud();wipi_end_native_hud();
  assert(fb_ptr()==g_phone_fb && g_screen_fb.buf==0x02010000);
  assert(as_fb(0x02001000)==cached && cached->buf==0x02010000);
 }
 wipi_present();assert(log_draws==1);
 for(int i=0;i<256*192;i++){
  const uint16_t expected=(i==191*256+239)?0x07e0:0xf800;
  assert(g_ds_fb[i]==rgb565_to_ds15(expected));
  assert(g_sub_fb[i]==(BIT(15)|RGB15(0,0,0)));
  assert(g_phone_fb[i]==expected);
 }
 // Static SUB is not rebuilt, but TOP must keep accepting changed pixels.
 for(int frame=0;frame<8;frame++){
  g_phone_fb[0]=(uint16_t)frame;wipi_present();
  assert(log_draws==1 && g_ds_fb[0]==rgb565_to_ds15((uint16_t)frame));
 }
 g_phone_fb[0]=0xf800;
 g_log_visible=true;g_sub_fb[100]=123;wipi_present();assert(g_sub_fb[100]==123 && log_draws==1);
 auto *save=g_phone_fb;g_phone_fb=nullptr;
 assert(!wipi_begin_native_hud() && !g_native_hud_active && g_screen_fb.buf==0x02010000);
 g_phone_fb=save;
 g_clet.started=true;g_clet.callbacks[4]=(uint32_t)(uintptr_t)&paint_probe;
 paint_region(0,0,256,192);assert(!g_in_paint);
 paint_region(0,0,256,192);assert(!g_in_paint);
 g_log_visible=false;g_sub_static_valid=false;wipi_present();assert(log_draws==2);
 for(int i=0;i<256*192;i++)assert(g_sub_fb[i]==(BIT(15)|RGB15(0,0,0)));
 g_minimap_fb=(uint16_t*)0x020b0000;g_minimap_ready=true;
 assert(!wipi_begin_minimap(88,36));wipi_toggle_minimap();assert(g_minimap_bottom && g_repaint_pending);
 assert(wipi_begin_minimap(88,36));assert(!wipi_begin_minimap(88,36));
 assert(g_minimap_w==92 && g_minimap_h==40 && fb_ptr()==g_minimap_fb && g_screen_fb.buf==0x020b0000);
 assert(as_fb(0x02001000)!=cached && cached->buf==0x02010000);
 assert(fb_pixels16(as_fb(0x02001000))==g_minimap_fb);
 assert(as_fb(0x02001040)==image && image->buf==0x02090000);
 assert(!wipi_minimap_has_pixels());
 fb_pixels16(as_fb(0x02001000))[257]=0xffff;
 assert(wipi_minimap_has_pixels());wipi_end_minimap();
 // Dynamic SUB must update every frame, even though static SUB is cached.
 int prior_draws=log_draws;wipi_present();wipi_present();
 assert(log_draws==prior_draws+2 && !g_sub_static_valid);
 assert(g_minimap_valid && !g_minimap_capture && fb_ptr()==g_phone_fb && g_screen_fb.buf==0x02010000);
 assert(as_fb(0x02001000)==cached && g_phone_fb[257]==0xf800);
 assert(wipi_begin_minimap(39,71));assert(!wipi_minimap_has_pixels());wipi_end_minimap();assert(!g_minimap_valid);
 assert(!wipi_begin_minimap(253,36) && !wipi_begin_minimap(88,125));
 wipi_toggle_minimap();assert(!g_minimap_bottom);assert(!wipi_begin_minimap(88,36));
 assert(!g_sub_static_valid);wipi_present();assert(g_sub_static_valid);
 prior_draws=log_draws;wipi_present();assert(log_draws==prior_draws);
 puts("PASS v053 static SUB caching, dynamic minimap refresh, TOP updates and transitions");
 puts("PASS minimap scoped capture, cached screen redirection, offscreen isolation, TOP untouched, invalid/early-return clearing, toggle restore");
 puts("PASS actual WIPI TOP scope + cached descriptor + offscreen isolation + HUD pixel on TOP, 100 repeats; SUB black/LOG only, LOG close clears stale pixels; fake4-9 absent");
}'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17','-no-pie',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
