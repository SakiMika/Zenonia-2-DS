#include "zen_native_layout.h"
#include "zen_native_layout_policy.h"
#include "wipi_shim.h"
#include <malloc.h>
#include <stdio.h>
#include <string.h>

namespace {
using GuiLoadFn = uint32_t (*)(uint32_t,const char*,uint32_t);
static GuiLoadFn original_load=nullptr;
static void *loader_trampoline=nullptr;
static unsigned load_count=0;
using TitleDrawFn = uint32_t (*)(uint32_t,int,int,uint32_t,uint32_t,uint32_t);
static TitleDrawFn original_title_draw=nullptr;
// GUI labels use a different renderer from Title_1 background animations.
using TitleGuiDrawFn = uint32_t (*)(uint32_t,int,int,int,uint32_t,uint32_t);
static TitleGuiDrawFn original_title_gui_draw=nullptr;
extern "C" uint32_t zen_title_gui_draw(uint32_t gui,int x,int y,int group,
                                       uint32_t sprites,uint32_t order) {
    return original_title_gui_draw(gui,x+ZenNativeLayout::TitleShiftX,y+ZenNativeLayout::TitleLabelsShiftY,
                                   group,sprites,order);
}

// Only the two private title-screen literal pools use this wrapper. The
// shared animation renderer remains untouched for gameplay and other menus.
extern "C" uint32_t zen_title_animation_draw(uint32_t animation,int x,int y,
                                            uint32_t mode,uint32_t a,uint32_t b) {
    return original_title_draw(animation,x+ZenNativeLayout::TitleShiftX,y+ZenNativeLayout::TitleAnimationShiftY,mode,a,b);
}

static bool ram(uint32_t p,unsigned n) {
    return p>=0x02000000u && p<0x03000000u && n<=0x03000000u-p;
}
static bool read_word(uint32_t p,uint32_t &v) {
    if((p&3u) || !ram(p,4)) return false;
    memcpy(&v,(void*)(uintptr_t)p,4); return true;
}
// Dialogue has a dedicated geometry helper (only five callers, all in the
// 1c0d0..1c92e dialogue class) and a private GUI-draw literal. Move BOTH.
// Bounds drive text, speaker name, portrait anchor and continue/choice widgets.
// Do not modify the screen/camera context or font metrics.
using DialogueRectFn = uint32_t (*)(uint32_t,uint32_t);
static DialogueRectFn original_dialogue_rect=nullptr;
static TitleGuiDrawFn original_dialogue_gui=nullptr;
extern "C" uint32_t zen_dialogue_rect(uint32_t out,uint32_t group) {
    const uint32_t result=original_dialogue_rect(out,group);
    if(group>=4 && group<=8 && !(out&1u) && ram(out,8)) {
        int16_t rect[4];memcpy(rect,(void*)(uintptr_t)out,8);
        rect[1]=(int16_t)(rect[1]+ZenNativeLayout::DialogueShiftY);
        memcpy((void*)(uintptr_t)out,rect,8);
    }
    return result;
}
extern "C" uint32_t zen_dialogue_gui_draw(uint32_t gui,int x,int y,int group,
                                         uint32_t sprites,uint32_t order) {
    // Private literal used only by 1c328, groups4..8 (body + speaker tabs).
    return original_dialogue_gui(gui,x,y+((group>=4 && group<=8)?
        ZenNativeLayout::DialogueShiftY:0),group,sprites,order);
}
// v042: move the complete native HUD span of 2033c to TOP Y132..191.
// Keep v041 sprite/rect alignment, but draw into the gameplay framebuffer.
// 1e9f4 starts the clock/status tail; restore geometry BEFORE it runs.
// Context 1220+40 is the scene viewport offset, NOT graphics font-height +40.
using HudFn = uint32_t (*)(uint32_t);
using ContextFn = uint32_t (*)();
static HudFn original_hud=nullptr,original_hud_top_tail=nullptr;
static ContextFn hud_context=nullptr;
static uint32_t hud_items[11]={};
static unsigned hud_item_count=0;
static uint32_t hud_gui=0;
// Change only GameUI's authored sprite coordinates, not the raster origin.
// Native 171f8/1f5a0 subtract context+40, but c844 adds it back before
// storing pixels. Using +128 as a layout shift wrote beyond a 192-row FB.
struct HudY { uint32_t address; int16_t saved; };
static HudY hud_sprite_y[24];
static unsigned hud_sprite_y_count=0;
static bool hud_collect_sprites() {
    hud_sprite_y_count=0;
    uint32_t owner=0,manager=0,table=0,count=0;
    if(!read_word(hud_gui+12,owner) || !read_word(owner+12,manager) ||
       !read_word(manager+8,table) || !read_word(manager+16,count) ||
       count!=10 || !ram(table,40)) return false;
    const unsigned groups[4]={1,2,3,9},counts[4]={4,11,1,1};
    for(unsigned g=0;g<4;g++) {
        uint32_t sprite=0,fragments=0;
        if(!read_word(table+groups[g]*4,sprite) || !ram(sprite,24) ||
           *(const uint8_t*)(uintptr_t)(sprite+12)!=counts[g] ||
           !read_word(sprite+8,fragments) || !ram(fragments,counts[g]*24))
            return false;
        for(unsigned j=0;j<counts[g];j++) {
            const uint32_t a=fragments+j*24+6;
            int16_t y;memcpy(&y,(void*)(uintptr_t)a,2);
            if(y<256 || y>319 || hud_sprite_y_count>=24) return false;
            hud_sprite_y[hud_sprite_y_count++]={a,y};
        }
        // Bounds are read separately by portrait overlays. Shift a real
        // bottom-panel bound too; a zero/uncomputed bound is left alone.
        int16_t y;memcpy(&y,(void*)(uintptr_t)(sprite+16),2);
        if(y>=256 && y<=319) {
            if(hud_sprite_y_count>=24) return false;
            hud_sprite_y[hud_sprite_y_count++]={sprite+16,y};
        }
    }
    return true;
}
static bool hud_scope=false;
static bool hud_geometry_warned=false;
static void hud_finish() {
    if(!hud_scope) return;
    for(unsigned i=0;i<hud_sprite_y_count;i++)
        memcpy((void*)(uintptr_t)hud_sprite_y[i].address,&hud_sprite_y[i].saved,2);
    hud_sprite_y_count=0;
    for(unsigned i=0;i<11;i++) {
        int16_t *r=(int16_t*)(uintptr_t)(hud_items[i]+8);
        r[1]=(int16_t)(r[1]+64);
    }
    wipi_end_native_hud();
    hud_scope=false;
}
extern "C" uint32_t zen_native_hud_draw(uint32_t self) {
    if(hud_scope) return original_hud(self); // no nested coordinate shifts
    uint32_t context=hud_context?hud_context():0;
    bool ready=hud_item_count==11 && ram(context,0x44);
    for(unsigned i=0;ready && i<11;i++) {
        const uint32_t item=hud_items[i];
        if(!ram(item,16) || (item&1u)) {ready=false;break;}
        int16_t r[4];memcpy(r,(void*)(uintptr_t)(item+8),8);
        // Loader already applied -64; apply the remaining -64 only while HUD paints.
        if(r[1]<192 || r[1]>255 || r[3]<1 || r[3]>48 || r[1]+r[3]>256)
            ready=false;
    }
    const bool sprites_ready=ready && hud_collect_sprites();
    if(ready && !sprites_ready && !hud_geometry_warned) {
        printf("[HUD042!] PZX geometry differs; HUD relocation skipped\n");
        hud_geometry_warned=true;
    }
    if(sprites_ready && wipi_begin_native_hud()) {
        for(unsigned i=0;i<hud_sprite_y_count;i++) {
            const int16_t y=(int16_t)(hud_sprite_y[i].saved-128);
            memcpy((void*)(uintptr_t)hud_sprite_y[i].address,&y,2);
        }
        for(unsigned i=0;i<11;i++) {
            int16_t *r=(int16_t*)(uintptr_t)(hud_items[i]+8);
            r[1]=(int16_t)(r[1]-64);
        }
        hud_scope=true;
    }
    const uint32_t result=original_hud(self);
    hud_finish(); // also covers an early-return or a future path without the tail
    return result;
}
extern "C" uint32_t zen_native_hud_top_tail(uint32_t self) {
    hud_finish();
    return original_hud_top_tail(self);
}
// Native script commands: +0 opcode, +8 argument array; arguments are
// 12-byte records with their evaluated/raw handle value at +4. Hook only
// opening resource 1:10 and narration strings 1:0..7 with exact original layout.
using ScriptOpFn = uint32_t (*)(uint32_t,uint32_t,uint32_t);
static bool scene_image_seen=false,scene_text_seen=false;
static ScriptOpFn original_scene_image=nullptr,original_scene_animation=nullptr,
                  original_scene_text=nullptr;
static uint32_t scene_call(ScriptOpFn fn,uint32_t self,uint32_t cmd,uint32_t flags,
                           bool text,bool animation) {
    uint32_t op=0,args=0;
    if(!read_word(cmd,op) || !read_word(cmd+8,args) ||
       op!=(text?18u:(animation?15u:14u)) || !ram(args,text?96:48))
        return fn(self,cmd,flags);
    uint32_t values[8]={};
    const unsigned n=text?8:4;
    for(unsigned i=0;i<n;i++) memcpy(values+i,(void*)(uintptr_t)(args+12*i+4),4);
    const bool match=text ? ZenNativeLayout::isOpeningNarration(values)
                          : ZenNativeLayout::isOpeningPicture(values);
    if(!match) return fn(self,cmd,flags);
    bool &seen=text?scene_text_seen:scene_image_seen;
    if(!seen) {
        printf(text?"[SCENE038] narration matched: y108 h80, original speed\n":
                    "[SCENE038] opening picture matched: anchor y58\n");
        seen=true;
    }
    const unsigned yslot=text?0:3;
    const uint32_t y=text?ZenNativeLayout::SceneTextY:ZenNativeLayout::SceneImageY;
    const uint32_t height=ZenNativeLayout::SceneTextHeight;
    memcpy((void*)(uintptr_t)(args+yslot*12+4),&y,4);
    if(text) memcpy((void*)(uintptr_t)(args+28),&height,4);
    const uint32_t result=fn(self,cmd,flags);
    // op18 yields and is called repeatedly. Restore script values after every
    // invocation so coordinates do not accumulate and matching remains exact.
    memcpy((void*)(uintptr_t)(args+yslot*12+4),values+yslot,4);
    if(text) memcpy((void*)(uintptr_t)(args+28),values+2,4);
    return result;
}
extern "C" uint32_t zen_scene_image(uint32_t s,uint32_t c,uint32_t f) {
    return scene_call(original_scene_image,s,c,f,false,false);
}
extern "C" uint32_t zen_scene_animation(uint32_t s,uint32_t c,uint32_t f) {
    return scene_call(original_scene_animation,s,c,f,false,true);
}
extern "C" uint32_t zen_scene_text(uint32_t s,uint32_t c,uint32_t f) {
    return scene_call(original_scene_text,s,c,f,true,false);
}
// Native GUI arrays: vtable +0, pointer-table +4, element count +8.
static bool remap_game_ui(uint32_t parsed,unsigned &moved) {
    uint32_t outer=0,groups=0,table=0;
    if(!read_word(parsed,outer) || !read_word(outer+8,groups) ||
       !read_word(outer+4,table) || groups!=10 || !ram(table,groups*4)) return false;
    uint32_t items[11]; unsigned count=0;
    // Validate every record before changing any of them.
    for(uint32_t i=0;i<groups;i++) {
        uint32_t group=0,n=0,slots=0;
        if(!read_word(table+4*i,group) || !read_word(group+8,n) ||
           !read_word(group+4,slots) || n>11 || (n && !ram(slots,n*4))) return false;
        if(i!=2 && n) return false;
        for(uint32_t j=0;j<n;j++) {
            uint32_t item=0;
            if(count>=11 || !read_word(slots+4*j,item) || !ram(item,16)) return false;
            const uint8_t type=*(const uint8_t*)(uintptr_t)(item+5);
            if(!(type==1 || type==2 || type==3 || type==10)) return false;
            int16_t r[4]; memcpy(r,(void*)(uintptr_t)(item+8),8);
            if(!ZenNativeLayout::moveGameUiRect(r)) return false;
            items[count++]=item;
        }
    }
    if(count!=11) return false;
    for(unsigned i=0;i<count;i++) {
        int16_t *r=(int16_t*)(uintptr_t)(items[i]+8);
        r[1]=(int16_t)(r[1]+ZenNativeLayout::GameUiShiftY);
    }
    memcpy(hud_items,items,sizeof(items)); hud_item_count=count; hud_gui=parsed;
    moved=count; return true;
}
}

extern "C" uint32_t zen_native_gui_load_hook(uint32_t self,const char *name,uint32_t owner) {
    if(!original_load) return 0;
    const uint32_t parsed=original_load(self,name,owner);
    if(parsed && ZenNativeLayout::isGameUiResource(name)) {
        unsigned n=0; hud_item_count=0; hud_gui=0; hud_geometry_warned=false;
        if(remap_game_ui(parsed,n)) {
            printf("[NUI] GameUI load=%u records=%u native dy=-64, final dy=-128\n",++load_count,n);
        } else {
            printf("[NUI!] GameUI layout differs; untouched. Do not treat HUD as verified.\n");
        }
    }
    return parsed;
}

bool zen_native_layout_install(LgtLoadedImage *img) {
    if(!img || !img->text || img->text_old!=0x1000u || img->text_size!=0x8b538u ||
       img->data_old!=0x01400000u || img->data_size!=0xf1cu) return false;
    // Original GUI loader at 0x17a68:
    // push {r4,r5,r6,lr}; sub sp,#4; mov r0,r1; ldr r3,[pc,#0x6c]
    const uint8_t expected[8]={0x70,0xb5,0x81,0xb0,0x08,0x1c,0x1b,0x4b};
    uint8_t *entry=(uint8_t*)lgt_translate_ptr(img,0x17a68u);
    const uint32_t *literal=(const uint32_t*)lgt_translate_ptr(img,0x17adcu);
    if(!entry || !literal || memcmp(entry,expected,8)) return false;
    // All guards are checked BEFORE mutating guest instructions. These two
    // literal slots are local to boot/title draw functions 0x5a634/0x5b338.
    // They must already contain the relocated original animation entry.
    uint32_t *title_intro=(uint32_t*)lgt_translate_ptr(img,0x5a908u);
    uint32_t *title_menu=(uint32_t*)lgt_translate_ptr(img,0x5b3ecu);
    uint32_t *press_gui=(uint32_t*)lgt_translate_ptr(img,0x5a030u);
    uint32_t *menu_gui=(uint32_t*)lgt_translate_ptr(img,0x5b534u);
    uint16_t *menu_text_y=(uint16_t*)lgt_translate_ptr(img,0x5b476u);
    const uint32_t gui_draw=(uint32_t)(uintptr_t)lgt_translate_ptr(img,0x17250u)|1u;
    if(!press_gui || !menu_gui || !menu_text_y || *press_gui!=gui_draw ||
       *menu_gui!=gui_draw || *menu_text_y!=0x3b0au) return false;
    uint16_t *notice_body=(uint16_t*)lgt_translate_ptr(img,0x5aa3eu);
    uint16_t *notice_y=(uint16_t*)lgt_translate_ptr(img,0x5aab0u);
    const uint32_t title_draw=(uint32_t)(uintptr_t)lgt_translate_ptr(img,0x70e84u)|1u;
    if(!title_intro || !title_menu || !notice_body || !notice_y ||
       *title_intro!=title_draw || *title_menu!=title_draw || *notice_body!=0x1040u || *notice_y!=0x33aau)
        return false;
    uint8_t *title_logo=(uint8_t*)lgt_translate_ptr(img,0x5a744u);
    const uint8_t logo_expected[8]={0x33,0x68,0x04,0x1c,0x1b,0x6a,0x30,0x1c};
    if(!title_logo || memcmp(title_logo,logo_expected,8)) return false;
    // Script opcode dispatch slots; all guards precede every write/allocation.
    const uint32_t scene_slots[3]={0x887f8u,0x88800u,0x88818u};
    const uint32_t scene_entries[3]={0x69eccu,0x69f2cu,0x6af60u};
    uint32_t *scene_pools[3]; uint32_t scene_originals[3];
    for(unsigned i=0;i<3;i++) {
        scene_pools[i]=(uint32_t*)lgt_translate_ptr(img,scene_slots[i]);
        scene_originals[i]=(uint32_t)(uintptr_t)lgt_translate_ptr(img,scene_entries[i])|1u;
        if(!scene_pools[i] || *scene_pools[i]!=scene_originals[i]) return false;
    }
    uint8_t *dialogue_entry=(uint8_t*)lgt_translate_ptr(img,0x1c07cu);
    const uint8_t dialogue_expected[8]={0x70,0xb5,0x10,0x4c,0x82,0xb0,0x06,0x1c};
    const uint32_t *dialogue_literal=(const uint32_t*)lgt_translate_ptr(img,0x1c0c0u);
    uint32_t *dialogue_gui=(uint32_t*)lgt_translate_ptr(img,0x1c660u);
    if(!dialogue_entry || !dialogue_literal || !dialogue_gui ||
       memcmp(dialogue_entry,dialogue_expected,8) || *dialogue_gui!=gui_draw) return false;
    uint8_t *hud_entry=(uint8_t*)lgt_translate_ptr(img,0x2033cu);
    uint8_t *hud_tail_entry=(uint8_t*)lgt_translate_ptr(img,0x1e9f4u);
    const uint8_t hud_expected[8]={0xf0,0xb5,0x3e,0x4c,0x8d,0xb0,0x01,0x21};
    const uint8_t hud_tail_expected[8]={0xf0,0xb5,0x38,0x4a,0x8e,0xb0,0x80,0x18};
    const uint32_t *hud_global=(const uint32_t*)lgt_translate_ptr(img,0x20438u);
    const uint32_t *tail_constant=(const uint32_t*)lgt_translate_ptr(img,0x1ead8u);
    if(!hud_entry || !hud_tail_entry || !hud_global || !tail_constant ||
       memcmp(hud_entry,hud_expected,8) || memcmp(hud_tail_entry,hud_tail_expected,8) ||
       *tail_constant!=0x4fbu) return false;
    uint8_t *tramp=(uint8_t*)memalign(32,160);
    if(!tramp) return false;
    memset(tramp,0,160);
    // Displaced Thumb instructions. Relocate the PC-relative LDR rather
    // than copying it blindly. Saved r4 can be scratch until the guest
    // overwrites it after its first call (confirmed in this binary).
    memcpy(tramp,expected,6);
    const uint16_t tail[5]={0x4b02,0x4c02,0x4720,0x46c0,0x46c0};
    memcpy(tramp+6,tail,sizeof(tail));
    const uint32_t original_literal=*literal; // already relocated by LGT loader
    const uint32_t resume=(uint32_t)(uintptr_t)(entry+8)|1u;
    memcpy(tramp+16,&original_literal,4); memcpy(tramp+20,&resume,4);
    loader_trampoline=tramp; // lifetime: entire game session
    original_load=(GuiLoadFn)((uintptr_t)loader_trampoline|1u);
    // Static bottom-anchored copyright has its own vertical position.
    // Do not move the title BG/logo or Press Any Key along with this line.
    uint8_t *logo_tramp=tramp+32;
    memcpy(logo_tramp,logo_expected,8);
    const uint16_t logo_tail[4]={(uint16_t)(0x3c00u-ZenNativeLayout::TitleCopyrightShiftY),0x4a01,0x4710,0x46c0};
    memcpy(logo_tramp+8,logo_tail,8); // sub r4,#32; ldr r2; bx r2; nop
    const uint32_t logo_resume=(uint32_t)(uintptr_t)(title_logo+8)|1u;
    memcpy(logo_tramp+16,&logo_resume,4);
    // Third 32-byte trampoline: displaced LDR r4 must use its relocated
    // global literal, not the original PC-relative displacement.
    uint8_t *dialogue_tramp=tramp+64;
    const uint16_t dialogue_code[8]={0xb570,0x4c03,0xb082,0x1c06,
                                    0x4b02,0x4718,0x46c0,0x46c0};
    memcpy(dialogue_tramp,dialogue_code,16);
    const uint32_t dialogue_global=*dialogue_literal;
    const uint32_t dialogue_resume=(uint32_t)(uintptr_t)(dialogue_entry+8)|1u;
    memcpy(dialogue_tramp+16,&dialogue_global,4);
    memcpy(dialogue_tramp+20,&dialogue_resume,4);
    original_dialogue_rect=(DialogueRectFn)((uintptr_t)dialogue_tramp|1u);
    original_dialogue_gui=(TitleGuiDrawFn)(uintptr_t)gui_draw;
    // Two additional 32-byte relocated prologues: HUD + upper clock tail.
    const uint16_t hud_code[8]={0xb5f0,0x4c03,0xb08d,0x2101,0x4b02,0x4718,0x46c0,0x46c0};
    const uint16_t hud_tail_code[8]={0xb5f0,0x4a03,0xb08e,0x1880,0x4b02,0x4718,0x46c0,0x46c0};
    memcpy(tramp+96,hud_code,16);memcpy(tramp+128,hud_tail_code,16);
    const uint32_t hud_resume=(uint32_t)(uintptr_t)(hud_entry+8)|1u;
    const uint32_t tail_resume=(uint32_t)(uintptr_t)(hud_tail_entry+8)|1u;
    memcpy(tramp+112,hud_global,4);memcpy(tramp+116,&hud_resume,4);
    memcpy(tramp+144,tail_constant,4);memcpy(tramp+148,&tail_resume,4);
    original_hud=(HudFn)((uintptr_t)(tramp+96)|1u);
    original_hud_top_tail=(HudFn)((uintptr_t)(tramp+128)|1u);
    hud_context=(ContextFn)((uintptr_t)lgt_translate_ptr(img,0x1220u)|1u);
    DC_FlushRange(tramp,160); IC_InvalidateRange(tramp,160);
    const uint16_t veneer[2]={0x4b00,0x4718}; // ldr r3,[pc,#0]; bx r3
    const uint32_t hook=(uint32_t)(uintptr_t)&zen_native_gui_load_hook;
    memcpy(entry,veneer,4); memcpy(entry+4,&hook,4);
    DC_FlushRange(entry,8); IC_InvalidateRange(entry,8);
    const uint16_t logo_veneer[2]={0x4a00,0x4710}; // ldr r2,[pc,#0]; bx r2
    const uint32_t logo_target=(uint32_t)(uintptr_t)logo_tramp|1u;
    memcpy(title_logo,logo_veneer,4); memcpy(title_logo+4,&logo_target,4);
    DC_FlushRange(title_logo,8); IC_InvalidateRange(title_logo,8);
    original_title_gui_draw=(TitleGuiDrawFn)(uintptr_t)gui_draw;
    *press_gui=(uint32_t)(uintptr_t)&zen_title_gui_draw;
    *menu_gui=(uint32_t)(uintptr_t)&zen_title_gui_draw;
    // Foreground menu formats the selected option twice (shadow + face).
    // Both use stack[0x14], calculated here, outside the GUI sprite path.
    // sub r3,#10 -> sub r3,#106 shifts BOTH passes by -96, no font changes.
    *menu_text_y=(uint16_t)(0x3b00u+10-ZenNativeLayout::TitleLabelsShiftY);
    DC_FlushRange(press_gui,4); IC_InvalidateRange(press_gui,4);
    DC_FlushRange(menu_gui,4); IC_InvalidateRange(menu_gui,4);
    DC_FlushRange(menu_text_y,2); IC_InvalidateRange(menu_text_y,2);
    original_title_draw=(TitleDrawFn)(uintptr_t)title_draw;
    *title_intro=(uint32_t)(uintptr_t)&zen_title_animation_draw;
    *title_menu=(uint32_t)(uintptr_t)&zen_title_animation_draw;
    // Body and blink prompt share a stored base. Move the body 16 -> 4,
    // then compensate the prompt offset so it stays at 166, NOT 154.
    // asrs r0,r0,#1 -> movs r0,#4; adds r3,#170 -> adds r3,#162.
    *notice_body=(uint16_t)(0x2000u+ZenNativeLayout::NoticeBodyY);
    *notice_y=(uint16_t)(0x3300u+ZenNativeLayout::NoticePromptOffsetY);
    DC_FlushRange(title_intro,4); IC_InvalidateRange(title_intro,4);
    DC_FlushRange(title_menu,4); IC_InvalidateRange(title_menu,4);
    DC_FlushRange(notice_body,2); IC_InvalidateRange(notice_body,2);
    DC_FlushRange(notice_y,2); IC_InvalidateRange(notice_y,2);
    original_scene_image=(ScriptOpFn)(uintptr_t)scene_originals[0];
    original_scene_animation=(ScriptOpFn)(uintptr_t)scene_originals[1];
    original_scene_text=(ScriptOpFn)(uintptr_t)scene_originals[2];
    const uint32_t scene_hooks[3]={(uint32_t)(uintptr_t)&zen_scene_image,
        (uint32_t)(uintptr_t)&zen_scene_animation,(uint32_t)(uintptr_t)&zen_scene_text};
    for(unsigned i=0;i<3;i++) {
        *scene_pools[i]=scene_hooks[i];
        DC_FlushRange(scene_pools[i],4); IC_InvalidateRange(scene_pools[i],4);
    }
    const uint32_t dialogue_hook=(uint32_t)(uintptr_t)&zen_dialogue_rect;
    memcpy(dialogue_entry,veneer,4);memcpy(dialogue_entry+4,&dialogue_hook,4);
    *dialogue_gui=(uint32_t)(uintptr_t)&zen_dialogue_gui_draw;
    DC_FlushRange(dialogue_entry,8);IC_InvalidateRange(dialogue_entry,8);
    DC_FlushRange(dialogue_gui,4);IC_InvalidateRange(dialogue_gui,4);
    const uint32_t hud_hook=(uint32_t)(uintptr_t)&zen_native_hud_draw;
    const uint32_t tail_hook=(uint32_t)(uintptr_t)&zen_native_hud_top_tail;
    memcpy(hud_entry,veneer,4);memcpy(hud_entry+4,&hud_hook,4);
    memcpy(hud_tail_entry,veneer,4);memcpy(hud_tail_entry+4,&tail_hook,4);
    DC_FlushRange(hud_entry,8);IC_InvalidateRange(hud_entry,8);
    DC_FlushRange(hud_tail_entry,8);IC_InvalidateRange(hud_tail_entry,8);
    printf("[HUD042] native HUD/quickbar -> TOP y132-191; no fake4-9 (SELECT map managed separately)\n");
    printf("[DIALOG039] frame/name/portrait/3 rows/advance dy=-128; font unchanged\n");
    printf("[SCENE038] opening image y110->58; text y108 h80; speed/font unchanged\n");
    printf("[NUI] native Thumb GUI-loader hook installed @17a68; no texture/font scaling\n");
    printf("[TITLE052] copyright lowered32px; BG/GUI/Press Any Key unchanged\n");
    return true;
}
