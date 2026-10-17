"""Compile actual defaults/dispatch/UI drawing from wipi_shim with hardware stubs."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1];src=(root/'source/wipi_shim.cpp').read_text()
def function(marker):
 a=src.index(marker)
 while ';' in src[a:src.index('{',a)]:a=src.index(marker,a+len(marker))
 b=src.index('{',a);depth=1;p=b+1
 while depth:
  if src[p]=='{':depth+=1
  elif src[p]=='}':depth-=1
  p+=1
 return src[a:p]+'\n'
code='''#include <stdint.h>
#include <cstdio>
#include <cstring>
#include <cassert>
#include <vector>
#include <utility>
#include <string>
#include <initializer_list>
enum { KEY_A=1,KEY_B=2,KEY_SELECT=4,KEY_START=8,KEY_RIGHT=16,KEY_LEFT=32,
 KEY_UP=64,KEY_DOWN=128,KEY_R=256,KEY_L=512,KEY_X=1024,KEY_Y=2048,KEY_TOUCH=4096,KEY_LID=8192 };
'''
a=src.index('constexpr int UI_TAB_SINGLE=');b=src.index('#pragma pack(push,4)',a);code+=src[a:b]
code+='''static uint32_t held=0;
uint32_t keysHeld(){return held;}
static std::vector<std::pair<int,int>> events;
void call_event(int type,int key){events.emplace_back(type,key);}
static uint32_t g_ui_single_map[UI_TARGET_COUNT],g_ui_combo_map1[UI_TARGET_COUNT],g_ui_combo_map2[UI_TARGET_COUNT];
static uint32_t g_ui_prev_logical=0;
static bool g_log_visible=false,g_ui_dirty=true,g_trace_next_timer=false,g_trace_repaint_once=false;
static unsigned g_db_trace_budget=0,g_unknown_trace_budget=0;
static int g_ui_tab=UI_TAB_SINGLE,g_ui_capture_single=-1,g_ui_capture_combo=-1;
static int g_ui_selected_single=0,g_ui_selected_combo=0;
static unsigned g_audio_play_count=0,g_audio_end_count=0,g_audio_fallback_bgm_count=0,g_audio_fallback_sfx_count=0;
static int g_audio_last_channel=0,g_ui_log_head=0,g_ui_log_count=0;
static char g_audio_last_bgm_asset[20],g_ui_log_lines[UI_LOG_CAP][32];
static void *g_log_console=(void*)1;
static std::string rows[24];
void consoleSelect(void*){}
void iprintf(const char*,...){}
int audio_asset_numeric_id(const char*){return 0;}
static int map_toggles=0;void wipi_toggle_minimap(){map_toggles++;}
void runner_ui_log_push_line(const char*){}
void runner_ui_set_row(int r,const char *s){assert(r>=0&&r<24);rows[r]=s;}
'''
code+='#include "'+str(root/'source/zen_boot_profile.h')+'"\nuint32_t zen_boot_clock_ms(void){return 0;}\n'
for marker in ['static void runner_ui_defaults(', 'static uint32_t runner_first_physical(',
 'static void runner_first_two_physical(', 'static const char *runner_physical_name(',
 'static void runner_format_mapping(', 'static void runner_ui_draw(',
 'static int runner_logical_wipi_for_bit(', 'static void runner_release_all_logical(',
 'void wipi_dispatch_keys(']:code+=function(marker)
code+='''
void setheld(uint32_t mask){uint32_t old=held;held=mask;wipi_dispatch_keys(mask&~old,old&~mask);}
void expect(std::initializer_list<int> keys){
 std::vector<int> got;
 for(int bit=0;bit<4+UI_TARGET_COUNT;bit++)if(g_ui_prev_logical&(1u<<bit))got.push_back(runner_logical_wipi_for_bit(bit));
 std::vector<int> want(keys);assert(got==want);
}
void stroke(uint32_t mask,int key){
 events.clear();setheld(mask);expect({key});
 assert(events.size()==1 && events[0]==std::make_pair(502,key));
 setheld(0);expect({});assert(events.size()==2 && events[1]==std::make_pair(503,key));
}
int main(){
 runner_ui_defaults();
 setheld(KEY_SELECT);assert(map_toggles==1);setheld(KEY_SELECT);assert(map_toggles==1);setheld(0);
 setheld(KEY_SELECT);assert(map_toggles==2);setheld(0);
 g_log_visible=true;setheld(KEY_SELECT);assert(map_toggles==2);setheld(0);g_log_visible=false;
 assert(UI_TARGET_COUNT==11 && UI_TARGET_TOP+UI_TARGET_COUNT*UI_TARGET_ROW_H==192);
 assert(std::string(g_runner_targets[0].name)=="OK" && g_runner_targets[0].wipi_key==-5);
 assert(std::string(g_runner_targets[1].name)=="CLR" && g_runner_targets[1].wipi_key==-16);
 assert(std::string(g_runner_targets[10].name)=="Call" && g_runner_targets[10].wipi_key==-10);
 stroke(KEY_A,-5);stroke(KEY_B,-16);stroke(KEY_R,'#');stroke(KEY_START,-10);
 stroke(KEY_X,'0');stroke(KEY_Y,'*');
 events.clear();setheld(KEY_SELECT);expect({});assert(events.empty());setheld(0);
 stroke(KEY_L|KEY_A,'1');stroke(KEY_L|KEY_B,'3');
 stroke(KEY_L|KEY_X,'7');stroke(KEY_L|KEY_Y,'9');
 events.clear();setheld(KEY_L);expect({});assert(events.empty());setheld(0);
 stroke(KEY_UP,-1);stroke(KEY_DOWN,-2);stroke(KEY_LEFT,-3);stroke(KEY_RIGHT,-4);
 // Add modifier after primary: old single releases, only numeric combo held.
 setheld(KEY_A);events.clear();setheld(KEY_A|KEY_L);expect({'1'});
 bool released=false,pressed=false;
 for(auto ev:events){if(ev==std::make_pair(503,-5))released=true;if(ev==std::make_pair(502,(int)'1'))pressed=true;}
 assert(released&&pressed);setheld(0);
 setheld(KEY_R|KEY_L|KEY_Y);expect({'9','#'});setheld(0);
 // Draw all eleven targets on SINGLE/COMBO: last row stays within LCD.
 g_log_visible=true;
 for(int tab:{UI_TAB_SINGLE,UI_TAB_COMBO}){
  g_ui_tab=tab;g_ui_dirty=true;runner_ui_draw();
  for(int i=0;i<UI_TARGET_COUNT;i++)assert(rows[2+i*2].find(g_runner_targets[i].name)!=std::string::npos);
  assert(rows[22].find("Call")!=std::string::npos && rows[23].empty());
 }
 g_ui_tab=UI_TAB_LOG;g_ui_dirty=true;ZenBootProfile::trace.hooks=true;
 runner_ui_draw();assert(!ZenBootProfile::trace.active);
 assert(rows[2]=="BOOT051 DIAG hooks:OK" && rows[14].find("PCM051")!=std::string::npos);
 // Real remap capture of CLR and Call: must not leak input to game.
 g_ui_capture_single=1;events.clear();setheld(KEY_SELECT);
 assert(g_ui_capture_single==1 && events.empty()); // SELECT is reserved.
 setheld(0);setheld(KEY_X);
 assert(g_ui_single_map[1]==KEY_X && g_ui_capture_single==-1 && events.empty());
 g_ui_single_map[8]=0; // Remove old X=0 for isolated remap assertion.
 setheld(0);stroke(KEY_X,-16);
 g_ui_capture_combo=10;events.clear();setheld(KEY_R|KEY_B);
 assert(g_ui_combo_map1[10] && g_ui_combo_map2[10] && g_ui_capture_combo==-1 && events.empty());
 setheld(0);stroke(KEY_R|KEY_B,-10);
 g_ui_capture_single=-1;g_ui_capture_combo=-1;
 setheld(KEY_Y);runner_release_all_logical();assert(g_ui_prev_logical==0);held=0;
 puts("PASS actual defaults + dispatcher: L+A/B/X/Y=1/3/7/9, R=#, A=OK, B=CLR, START=Call, X=0, Y=*, SELECT reserved toggle; combo suppression, key-up, D-pad, eleven UI rows, CLR/Call remap capture");
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
