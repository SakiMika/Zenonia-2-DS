#include "../source/zen_map_ui.h"
#include <cstdlib>
#include <cassert>
#include <cstdio>
#include <vector>
int main(int argc,char**argv){
 for(int w=1;w<=92;w++)for(int h=1;h<=75;h++){
  auto f=ZenMapUI::fit(w,h);assert(f.w>0 && f.h>0 && f.w<=224 && f.h<=116 && f.x>=16 && f.y>=48 && f.y+f.h<=164);
 }
 std::vector<uint16_t> out(256*192+2,0x1234),cap(256*192);
 if(argc>1){FILE *f=fopen(argv[1],"rb");assert(f);assert(fread(cap.data(),2,cap.size(),f)==cap.size());fclose(f);}
 int w=argc>2?atoi(argv[2]):43,h=argc>3?atoi(argv[3]):75;
 ZenMapUI::draw(out.data()+1,cap.data(),w,h,true);ZenMapUI::gear(out.data()+1);
 assert(out[0]==0x1234 && out.back()==0x1234);
 if(argc>4){FILE*f=fopen(argv[4],"wb");fprintf(f,"P6\n256 192\n255\n");for(int i=1;i<=256*192;i++){uint16_t p=out[i];unsigned char c[3]={(unsigned char)((p&31)*255/31),(unsigned char)(((p>>5)&31)*255/31),(unsigned char)(((p>>10)&31)*255/31)};fwrite(c,1,3,f);}fclose(f);}
 puts("PASS minimap fit: all 6900 bounding sizes; no framebuffer overrun; actual UI rendered");
}
