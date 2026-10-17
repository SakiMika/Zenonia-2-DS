#pragma once
#include <stdint.h>
#include "zen_map_art.h"
namespace ReferenceMapUI {
constexpr int GearX=236,GearY=4,GearSize=16;
inline uint16_t color(int r,int g,int b){return 0x8000|(r>>3)|((g>>3)<<5)|((b>>3)<<10);}
inline uint16_t from565(uint16_t p){return 0x8000|((p>>11)&31)|(((p>>6)&31)<<5)|((p&31)<<10);}
inline void rect(uint16_t *p,int x,int y,int w,int h,uint16_t c){
 for(int yy=y;yy<y+h;yy++)for(int xx=x;xx<x+w;xx++)if(xx>=0&&xx<256&&yy>=0&&yy<192)p[yy*256+xx]=c;
}
inline void border(uint16_t*p,int x,int y,int w,int h,uint16_t c){rect(p,x,y,w,1,c);rect(p,x,y+h-1,w,1,c);rect(p,x,y,1,h,c);rect(p,x+w-1,y,1,h,c);}
inline void gear(uint16_t *p){
 static const uint16_t rows[16]={0x0180,0x03c0,0x33cc,0x7ffe,0x3ffc,0x1e78,0x3c3c,0xfc3f,0xfc3f,0x3c3c,0x1e78,0x3ffc,0x7ffe,0x33cc,0x03c0,0x0180};
 rect(p,GearX,GearY,16,16,color(25,13,40));
 for(int y=0;y<16;y++)for(int x=0;x<16;x++)if(rows[y]&(1u<<(15-x)))p[(GearY+y)*256+GearX+x]=color(214,187,247);
}
struct Fit{int x,y,w,h;};
inline Fit fit(int w,int h){
 if(w<1||h<1)return {0,0,0,0};
 // Fractional nearest-neighbour zoom, capped at 4x. Both axes share a scale.
 int n=4*1024;if(224*1024/w<n)n=224*1024/w;if(116*1024/h<n)n=116*1024/h;
 int dw=w*n/1024,dh=h*n/1024;if(dw<1)dw=1;if(dh<1)dh=1;
 return {(256-dw)/2,48+(116-dh)/2,dw,dh};
}
inline void draw(uint16_t *out,const uint16_t *capture,int w,int h,bool valid){
 rect(out,0,0,256,192,color(20,11,32));rect(out,8,45,240,121,color(40,24,55));
 border(out,2,2,252,188,color(159,121,191));border(out,5,5,246,182,color(80,53,111));
 for(int y=0;y<22;y++)for(int x=0;x<234;x++)out[(23+y)*256+11+x]=place_bar[y*234+x];
 for(int y=0;y<29;y++)for(int x=0;x<35;x++)if((map_logo[y*35+x]&0x7fff)>0x421)out[(158+y)*256+213+x]=map_logo[y*35+x];
 if(!valid||!capture)return;
 Fit f=fit(w,h);
 for(int y=0;y<f.h;y++)for(int x=0;x<f.w;x++)out[(f.y+y)*256+f.x+x]=from565(capture[(y*h/f.h)*256+x*w/f.w]);
 // Native game-font title is captured in a separate scratch band, never ASCII replacement.
 int left=256,right=-1,top=160,bottom=127;
 for(int y=128;y<160;y++)for(int x=0;x<256;x++)if(capture[y*256+x]){if(x<left)left=x;if(x>right)right=x;if(y<top)top=y;if(y>bottom)bottom=y;}
 if(right>=left){int sw=right-left+1,sh=bottom-top+1,dw=sw<174?sw:174,dh=sh<14?sh:14;
  for(int y=0;y<dh;y++)for(int x=0;x<dw;x++){uint16_t c=capture[(top+y*sh/dh)*256+left+x*sw/dw];if(c)out[(27+(14-dh)/2+y)*256+(256-dw)/2+x]=from565(c);}
 }
}
}
