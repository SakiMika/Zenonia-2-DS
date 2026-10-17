#include "../source/zen_native_layout_policy.h"
#include <assert.h>
#include <stdio.h>
int main() {
    using namespace ZenNativeLayout;
    assert(isGameUiResource("com/GameUI.gui")); assert(isGameUiResource("GameUI.gui"));
    assert(!isGameUiResource("com/MainUI.gui")); assert(!isGameUiResource("GameUI.gui.backup"));
    const int16_t rects[11][4]={
      {95,289,98,4},{95,296,98,4},{1,318,45,1},
      {87,303,15,15},{113,303,15,15},{139,303,15,15},{165,303,15,15},
      {204,300,16,16},{189,275,46,22},{39,315,1,1},{56,291,17,6}
    };
    for(auto &src:rects) {
        int16_t r[4]={src[0],src[1],src[2],src[3]};
        assert(moveGameUiRect(r));
        assert(r[0]==src[0] && r[2]==src[2] && r[3]==src[3]);
        int final_y=r[1]+LayoutCenterY;
        assert(final_y==src[1]-128 && final_y>=0 && final_y+r[3]<=192);
    }
    int16_t map[4]={32,150,16,16};assert(!moveGameUiRect(map));assert(map[1]==150);
    printf("PASS: exact resource routing, 11 HUD rects, original sizes, final bounds\n");
}
