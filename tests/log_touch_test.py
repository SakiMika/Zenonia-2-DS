"""Compile the actual touch handler with UI side effects stubbed.
Verify every gameplay-screen pixel is inert except LOG; SINGLE/COMBO capture
selection and CLOSE remain usable. Physical key capture itself is unchanged.
"""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
src=(root/'source/wipi_shim.cpp').read_text()
a=src.index('void wipi_handle_touch(');b=src.index('\nvoid wipi_debug_dump(',a)
code='''#include <stdint.h>
#include <cassert>
#include <cstdio>
constexpr uint32_t KEY_TOUCH=1;
enum { UI_TAB_SINGLE, UI_TAB_COMBO, UI_TAB_LOG };
constexpr int DS_H=192;
static bool g_log_visible=false,g_ui_dirty=false;
static int g_ui_tab=UI_TAB_LOG,g_ui_capture_single=-1,g_ui_capture_combo=-1;
static int g_ui_selected_single=-1,g_ui_selected_combo=-1,draws=0;
void wipi_set_log_visible(bool v){g_log_visible=v;}
void runner_ui_draw(){draws++;}
'''
for name in ['LOG_BTN_X','LOG_BTN_Y','LOG_BTN_W','LOG_BTN_H','UI_TARGET_COUNT','UI_TARGET_TOP','UI_TARGET_ROW_H']:
 code+=re.search(r'constexpr int '+name+r'=\d+;',src)[0]+'\n'
code+=src[a:b]
code+='''int main(){
 for(int y=0;y<192;y++)for(int x=0;x<256;x++){
  g_log_visible=false;g_ui_dirty=false;draws=0;
  wipi_handle_touch(KEY_TOUCH,x,y);
  const bool inlog=x>=LOG_BTN_X && x<LOG_BTN_X+LOG_BTN_W && y>=LOG_BTN_Y && y<LOG_BTN_Y+LOG_BTN_H;
  assert(g_log_visible==inlog && !g_ui_dirty && draws==0);
 }
 g_log_visible=false;wipi_handle_touch(0,LOG_BTN_X,LOG_BTN_Y);assert(!g_log_visible);
 wipi_handle_touch(KEY_TOUCH,LOG_BTN_X,LOG_BTN_Y);assert(g_log_visible);
 wipi_handle_touch(KEY_TOUCH,10,10);assert(g_ui_tab==UI_TAB_SINGLE);
 for(int i=0;i<UI_TARGET_COUNT;i++){
  wipi_handle_touch(KEY_TOUCH,10,UI_TARGET_TOP+UI_TARGET_ROW_H*i);
  assert(g_ui_capture_single==i && g_ui_selected_single==i && g_ui_capture_combo==-1);
 }
 wipi_handle_touch(KEY_TOUCH,80,10);assert(g_ui_tab==UI_TAB_COMBO);
 for(int i=0;i<UI_TARGET_COUNT;i++){
  wipi_handle_touch(KEY_TOUCH,10,UI_TARGET_TOP+UI_TARGET_ROW_H*i);
  assert(g_ui_capture_combo==i && g_ui_selected_combo==i && g_ui_capture_single==-1);
 }
 wipi_handle_touch(KEY_TOUCH,160,10);assert(g_ui_tab==UI_TAB_LOG);
 wipi_handle_touch(KEY_TOUCH,220,10);assert(!g_log_visible);
 puts("PASS actual touch handler: all 49152 pixels LOG-only during gameplay; SINGLE/COMBO 11 capture rows and CLOSE preserved");
}'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
