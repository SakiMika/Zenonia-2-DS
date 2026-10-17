"""Compile actual timer/media callback paths with cache mode both off and on."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1];s=(r/'source/wipi_shim.cpp').read_text()
def func(marker):
 a=s.index(marker);p=s.index('{',a)+1;depth=1
 while depth:
  if s[p]=='{':depth+=1
  elif s[p]=='}':depth-=1
  p+=1
 return s[a:p]
code='''#include <cstdint>
#include <cassert>
#include <cstdio>
constexpr int TIMER_SLOTS=32;
struct TimerSlot{void*timer;void(*callback)(void*,void*);void*param;uint64_t due_ms;bool armed;};
static TimerSlot g_timers[TIMER_SLOTS]{};
static struct{int timer_fire=0;}g_trace;
static bool g_trace_next_timer=true;
static int flushes=0,invalidates=0,calls=0;
uint64_t timer_now_ms(){return 100;}
void DC_FlushAll(){++flushes;}
void IC_InvalidateAll(){++invalidates;}
namespace ZenBootProfile{enum Kind{Timer};}
struct BootCostScope{BootCostScope(ZenBootProfile::Kind){}};
void callback(void*timer,void*param){assert(timer==(void*)123 && param==(void*)456);++calls;}
struct DummyMediaClip{uint32_t callback;};
bool valid_ptr(uint32_t p){return p!=0;}
void media_callback(uint32_t,int event,int parm){assert(event==7 && parm==9);++calls;}
'''+func('static void process_timers(')+func('static void media_notify(')+'''
int main(){
 g_timers[0]={(void*)123,&callback,(void*)456,99,true};
 g_timers[1]={(void*)789,&callback,nullptr,101,true};
 process_timers();assert(calls==1 && !g_timers[0].armed && g_timers[1].armed && g_trace.timer_fire==1);
 process_timers();assert(calls==1);
 DummyMediaClip clip{(uint32_t)(uintptr_t)&media_callback};
 media_notify(&clip,7,9);assert(calls==2);
 clip.callback=0;media_notify(&clip,7,9);media_notify(nullptr,7,9);assert(calls==2);
 assert(flushes==(ZEN_CONSERVATIVE_CALLBACK_CACHE?2:0));
 assert(invalidates==flushes);
 puts("PASS actual timer/media callback dispatch, due/armed checks, cache compatibility mode");
}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'test.cpp').write_text(code)
 # Keep test callbacks inside the guest-valid ARM9 address window.
 for mode in (0,1):
  subprocess.run(['g++','-std=c++17','-no-pie','-Wl,-Ttext-segment=0x02000000','-DZEN_CONSERVATIVE_CALLBACK_CACHE='+str(mode),str(d/'test.cpp'),'-o',str(d/'test')],check=True)
  subprocess.run([str(d/'test')],check=True)
