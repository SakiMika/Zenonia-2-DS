#pragma once
#include <stdint.h>
#include "zen_map_art.h"
#include "zen_render_fast.h"
namespace ZenMapUI {
constexpr int GearX=236,GearY=4,GearSize=16;
inline uint16_t color(int r,int g,int b){return 0x8000|(r>>3)|((g>>3)<<5)|((b>>3)<<10);}
inline uint16_t from565(uint16_t p){return 0x8000|((p>>11)&31)|(((p>>6)&31)<<5)|((p&31)<<10);}
inline void rect(uint16_t *p,int x,int y,int w,int h,uint16_t c){
 if(!p || w<=0 || h<=0)return;
 int x1=x+w,y1=y+h;
 if(x<0)x=0;if(y<0)y=0;if(x1>256)x1=256;if(y1>192)y1=192;
 if(x>=x1 || y>=y1)return;
 if(x==0 && x1==256)ZenRenderFast::fill16(p+y*256,size_t(y1-y)*256,c);
 else for(int yy=y;yy<y1;yy++)ZenRenderFast::fill16(p+yy*256+x,x1-x,c);
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
 // ARM9 has no hardware divide: map X once, and Y once per row.
 int source_x[224];for(int x=0;x<f.w;x++)source_x[x]=x*w/f.w;
 for(int y=0;y<f.h;y++){
  const uint16_t *row=capture+(y*h/f.h)*256;
  uint16_t *dst=out+(f.y+y)*256+f.x;
  for(int x=0;x<f.w;x++)dst[x]=from565(row[source_x[x]]);
 }
 // Native game-font title is captured in a separate scratch band, never ASCII replacement.
 int left=256,right=-1,top=160,bottom=127;
 for(int y=128;y<160;y++)for(int x=0;x<256;x++)if(capture[y*256+x]){if(x<left)left=x;if(x>right)right=x;if(y<top)top=y;if(y>bottom)bottom=y;}
 if(right>=left){int sw=right-left+1,sh=bottom-top+1,dw=sw<174?sw:174,dh=sh<14?sh:14;
  int *title_x=source_x;int sx=0,ex=0; // Reuse map lookup storage; no extra title table on stack.
  for(int x=0;x<dw;x++){title_x[x]=left+sx;ex+=sw;while(ex>=dw){ex-=dw;++sx;}}
  int sy=0,ey=0;
  for(int y=0;y<dh;y++){
   const uint16_t *row=capture+(top+sy)*256;
   uint16_t *dst=out+(27+(14-dh)/2+y)*256+(256-dw)/2;
   for(int x=0;x<dw;x++){uint16_t c=row[title_x[x]];if(c)dst[x]=from565(c);}
   ey+=sh;while(ey>=dh){ey-=dh;++sy;}
  }
 }
}
}
