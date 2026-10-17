#pragma once
#include <stdint.h>
namespace ZenNativeLayout {
constexpr int Width = 256;
constexpr int Height = 192;
constexpr int LegacyWidth = 240;
constexpr int LegacyHeight = 320;
// Center the authored240px title canvas within the256px DS LCD.
// Only title background/GUI wrappers use this; native static logos and menu
// text already calculate their own center from the LCD width.
constexpr int TitleShiftX = (Width-LegacyWidth)/2; // +8; no image scaling
// Center the legacy title artwork vertically without changing its pixel size.
// This applies to artwork only; do not assume animation records are text labels.
constexpr int TitleAnimationShiftY = -64; // 32px lower than v035
// The static bottom-anchored image is the copyright line, not the BG/logo.
// Its own bottom is160, leaving space above Press Any Key at169.
constexpr int TitleCopyrightShiftY = -32; // +32px vs v051's -64
constexpr int TitleLabelsShiftY = -96; // Title.pzx GUI + selected menu text, not BG
constexpr int SceneImageY = 58; // original anchor110; 100px art starts near Y3
constexpr int SceneTextY = 108;
constexpr int SceneTextHeight = 80; // ends188, within upper LCD; 30px windows grow
inline bool isOpeningPicture(const uint32_t *v) {
    return v && v[0]==0x1000au && (v[1]<=7 || v[1]==18 || v[1]==19) &&
           v[2]==120 && v[3]==110;
}
inline bool isOpeningNarration(const uint32_t *v) {
    return v && (v[0]==200 || v[0]==185) && v[1]==170 &&
           (v[2]==30 || v[2]==80) && v[3]>=0x10000u && v[3]<=0x10007u &&
           v[4]==255 && v[5]==255 && v[6]==255 && (v[7]==1 || v[7]==2);
}
constexpr int DialogueShiftY = -128; // bottom320 ->192, all three rows together
constexpr int NoticeBodyY = 4;           // v035 body was 16
constexpr int NoticePromptY = 166;       // retain the already lifted blink prompt
constexpr int NoticePromptOffsetY = NoticePromptY-NoticeBodyY; // 162
constexpr int LayoutCenterY = (Height-LegacyHeight)/2; // original guest helper: -64
// GameUI.gui is a specifically identified bottom-HUD resource, NOT a rule
// applied to arbitrary map/sprite draw coordinates. Its entire group moves
// together; the scoped HUD wrapper supplies the remaining -64.
constexpr int GameUiShiftY = (Height-LegacyHeight)-LayoutCenterY; // -64
inline bool isGameUiResource(const char *name) {
    if(!name) return false;
    const char *leaf=name;
    for(const char *p=name;*p;p++) if(*p=='/' || *p=='\\') leaf=p+1;
    const char expected[]="GameUI.gui";
    unsigned i=0;
    while(expected[i] && leaf[i]==expected[i]) i++;
    return expected[i]==0 && leaf[i]==0;
}
inline bool moveGameUiRect(int16_t *rect) {
    if(!rect) return false;
    // The checked GameUI resource only contains bottom HUD rectangles.
    // Refuse another revision rather than partially remapping unknown layouts.
    const int y=rect[1],h=rect[3];
    if(y<256 || y>319 || h<1 || h>48 || y+h>320) return false;
    rect[1]=(int16_t)(y+GameUiShiftY);
    return true;
}
}
