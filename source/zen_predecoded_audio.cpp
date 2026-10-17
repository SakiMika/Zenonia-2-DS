#include "zen_predecoded_audio.h"
#include "embedded_assets.h"
#include "zen_title_pcm_manifest.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <malloc.h>
namespace {
static uint32_t fnv1a(const uint8_t *b,uint32_t n) {
 uint32_t h=2166136261u;
 for(uint32_t i=0;i<n;++i) h=(h^b[i])*16777619u;
 return h;
}
static uint32_t le32(const uint8_t *p) {
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
}
int zen_load_title_pcm(const uint8_t *encoded,uint32_t size,ZenDecodedPcm *out) {
 if(out) *out=ZenDecodedPcm{};
 if(!encoded || !out || size!=TITLE_PCM_SOURCE_SIZE ||
    fnv1a(encoded,size)!=TITLE_PCM_SOURCE_HASH) return 0;
 char path[192];
 if(!embedded_asset_path("runner_audio/title108.zpc",path,sizeof(path))) return -1;
 FILE *f=fopen(path,"rb");
 if(!f) return -1;
 uint8_t h[32];
 if(fread(h,1,sizeof h,f)!=sizeof h || memcmp(h,"ZPCM051\0",8) ||
    le32(h+8)!=size || le32(h+12)!=TITLE_PCM_SOURCE_HASH ||
    le32(h+16)!=8000u || le32(h+20)!=TITLE_PCM_SAMPLES ||
    le32(h+24)!=TITLE_PCM_SAMPLES*2u || le32(h+28)!=TITLE_PCM_HASH) {
  fclose(f);return -1;
 }
 const uint32_t bytes=TITLE_PCM_SAMPLES*2u;
 int16_t *pcm=(int16_t*)memalign(32,bytes);
 if(!pcm) { fclose(f);return -1; }
 const bool complete=fread(pcm,1,bytes,f)==bytes;
 const bool exact_size=complete && fgetc(f)==EOF && !ferror(f);
 fclose(f);
 if(!exact_size || fnv1a((const uint8_t*)pcm,bytes)!=TITLE_PCM_HASH) {
  free(pcm);return -1;
 }
 out->pcm=pcm;out->samples=TITLE_PCM_SAMPLES;out->rate=8000u;
 return 1;
}
