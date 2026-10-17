"""Host test of exact runtime cache glue. Not ARM hardware or FPS."""
from pathlib import Path
import tempfile,subprocess
r=Path(__file__).resolve().parents[1];s=(r/'source/wipi_shim.cpp').read_text()
def func(marker):
 a=s.index(marker);b=s.index('{',a);depth=1;p=b+1
 while depth:
  if s[p]=='{':depth+=1
  elif s[p]=='}':depth-=1
  p+=1
 return s[a:p]
code='''#include "zen_ds_policy.h"
#include <cassert>
#include <cstdio>
static bool g_minimap_bottom=true,g_minimap_valid=false;
static ZenDS::MinimapCache g_minimap_cache;
static uint32_t now_ms=0;
static uint64_t real_monotonic_ms(){return now_ms;}
'''+func('void wipi_invalidate_minimap_cache(')+'\n'+func('bool wipi_try_cached_minimap(')+'\n'+func('void wipi_store_minimap_cache(')+'''
int main(){
 uint32_t result=0;
 now_ms=1000;assert(!wipi_try_cached_minimap(1,2,88,36,&result));
 now_ms=1180;g_minimap_valid=true;wipi_store_minimap_cache(0xbeef);
 now_ms=1196;g_minimap_valid=false;
 assert(wipi_try_cached_minimap(1,2,88,36,&result) && result==0xbeef && g_minimap_valid);
 assert(g_minimap_cache.hits==1 && g_minimap_cache.draws==1 && g_minimap_cache.max_cost_ms==180);
 now_ms=1429;assert(wipi_try_cached_minimap(1,2,88,36,&result));
 now_ms=1430;assert(!wipi_try_cached_minimap(1,2,88,36,&result));
 now_ms=1432;g_minimap_valid=true;wipi_store_minimap_cache(7);
 now_ms=1433;assert(!wipi_try_cached_minimap(1,3,88,36,&result)); // map changes immediately
 now_ms=1434;g_minimap_valid=false;wipi_store_minimap_cache(0);
 now_ms=1435;assert(!wipi_try_cached_minimap(1,3,88,36,&result)); // no stale early return
 g_minimap_bottom=false;assert(!wipi_try_cached_minimap(1,3,88,36,&result) && !g_minimap_cache.initialized);
 puts("PASS actual cache glue: 180ms native draw no longer expires before reuse; complete-time wait, key changes, invalid/hidden fallback; diagnostic counters");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-O2','-std=c++17','-I'+str(r/'source'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
assert '#include "runner_package_config.h"' in s
assert 'g_minimap_cache.interval_ms=isDSiMode()?RUNNER_DSI_MINIMAP_INTERVAL_MS:RUNNER_DS_MINIMAP_INTERVAL_MS;' in s
h=(r/'source/zen_map_ui.h').read_text();assert 'x*w/f.w' not in h and 'y*h/f.h' not in h
assert 'MAP native%lu panel%lu ms' in s and 'MAP hit%lu draw%lu' in s and 'MAP wait%lu fallback%lu' in s
print('PASS DS/DSi rate configuration and on-device diagnostic wiring; per-coordinate scaling divisions removed')
