#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <malloc.h>
#include <cassert>
#include <string>
#include <vector>
#include <fstream>
#include <iterator>
#include <set>
bool embedded_asset_path(const char *name,char *out,size_t cap) {
 if(!name || strcmp(name,"runner_audio/title108.zpc"))return false;
 int n=snprintf(out,cap,"fat:/zenonia2nds/%s",name);return n>0 && (size_t)n<cap;
}
static std::string cache_path;
static bool fail_alloc=false,short_payload=false;
static unsigned opens=0,live_files=0;
static std::set<void*> allocations;
static FILE *cache_open(const char *path,const char *mode) {
 assert(std::string(path)=="fat:/zenonia2nds/runner_audio/title108.zpc");++opens;
 FILE *f=fopen(cache_path.c_str(),mode);if(f)++live_files;return f;
}
static int cache_close(FILE *f) { assert(live_files);--live_files;return fclose(f); }
static size_t cache_read(void *out,size_t a,size_t b,FILE *f) {
 if(short_payload && a*b>32) return fread(out,a,b-1,f);
 return fread(out,a,b,f);
}
static void *cache_alloc(size_t align,size_t n) {
 if(fail_alloc)return nullptr;
 void *p=memalign(align,n);if(p)allocations.insert(p);return p;
}
static void cache_free(void *p) { if(p) { assert(allocations.erase(p)==1);free(p); } }
#define fopen cache_open
#define fclose cache_close
#define fread cache_read
#define memalign cache_alloc
#define free cache_free
#include "../source/zen_predecoded_audio.cpp"
#undef fopen
#undef fclose
#undef fread
#undef memalign
#undef free
#include "../source/zen_boot_profile.h"
uint32_t zen_boot_clock_ms(void) { return 100; }
struct DummyMediaClip {
 uint8_t *data=nullptr;uint32_t data_len=0;
 int16_t *pcm=nullptr;uint32_t pcm_samples=0,sample_rate=0;uint8_t decoded_kind=0;
};
static unsigned synth_calls=0,wav_calls=0;
static int media_decode_smaf(DummyMediaClip*) { ++synth_calls;return -22; }
static int media_decode_wav(DummyMediaClip*) { ++wav_calls;return -23; }
static void media_release_pcm(DummyMediaClip *c) { cache_free(c->pcm);c->pcm=nullptr;c->pcm_samples=c->sample_rate=0; }
static void DC_FlushRange(const void*,unsigned){}
#include "audio_decode_entry.inc"
static std::vector<uint8_t> readall(const char *p) {
 std::ifstream f(p,std::ios::binary);return std::vector<uint8_t>((std::istreambuf_iterator<char>(f)),{});
}
static void writeall(const std::vector<uint8_t> &b) {
 FILE *f=fopen(cache_path.c_str(),"wb");assert(f);assert(fwrite(b.data(),1,b.size(),f)==b.size());fclose(f);
}
int main(int argc,char **argv) {
 assert(argc==2);cache_path=argv[1];
 const auto encoded=readall("zenonia2nds/sound/108.mmf");
 const auto packed=readall("zenonia2nds/runner_audio/title108.zpc");
 writeall(packed);ZenDecodedPcm out{};
 assert(zen_load_title_pcm(encoded.data(),encoded.size(),&out)==1);
 assert(out.samples==431010 && out.rate==8000 && (uintptr_t)out.pcm%32==0);
 assert(memcmp(out.pcm,packed.data()+32,out.samples*2)==0 && live_files==0);
 cache_free(out.pcm);
 auto other=encoded;other[20]^=1;unsigned old_opens=opens;
 assert(zen_load_title_pcm(other.data(),other.size(),&out)==0 && !out.pcm && opens==old_opens);
 assert(zen_load_title_pcm(nullptr,encoded.size(),&out)==0);
 assert(zen_load_title_pcm(encoded.data(),encoded.size(),nullptr)==0);
 // Real media_decode dispatch must bypass synthesis, reuse already decoded
 // PCM, preserve original fallback and counters without masking failures.
 DummyMediaClip c{};c.data=(uint8_t*)encoded.data();c.data_len=encoded.size();
 assert(media_decode(&c)==0 && c.decoded_kind==3 && synth_calls==0);
 assert(ZenBootProfile::trace.pcm_hits==1 && c.pcm_samples==431010);
 assert(media_decode(&c)==0 && ZenBootProfile::trace.pcm_hits==1);
 media_release_pcm(&c);
 std::remove(cache_path.c_str());
 assert(media_decode(&c)==-22 && synth_calls==1 && ZenBootProfile::trace.pcm_misses==1);
 assert(!c.pcm && live_files==0 && allocations.empty());
 c.data=other.data();c.data_len=other.size();
 assert(media_decode(&c)==-22 && synth_calls==2);
 uint8_t wav[12]={'R','I','F','F',0,0,0,0,'W','A','V','E'};
 c.data=wav;c.data_len=sizeof wav;assert(media_decode(&c)==-23 && wav_calls==1);
 c.data=nullptr;assert(media_decode(&c)==-1);
 for(unsigned pos:{0u,8u,12u,16u,20u,24u,28u,32u,431000u}) {
  auto bad=packed;bad[pos]^=1;writeall(bad);
  assert(zen_load_title_pcm(encoded.data(),encoded.size(),&out)==-1 && !out.pcm);
  assert(live_files==0 && allocations.empty());
 }
 for(unsigned n:{0u,16u,32u,100u,(unsigned)packed.size()-1}) {
  writeall(std::vector<uint8_t>(packed.begin(),packed.begin()+n));
  assert(zen_load_title_pcm(encoded.data(),encoded.size(),&out)==-1 && !out.pcm);
  assert(live_files==0 && allocations.empty());
 }
 auto extra=packed;extra.push_back(0);writeall(extra);
 assert(zen_load_title_pcm(encoded.data(),encoded.size(),&out)==-1 && allocations.empty());
 writeall(packed);fail_alloc=true;
 assert(zen_load_title_pcm(encoded.data(),encoded.size(),&out)==-1 && !out.pcm && live_files==0);
 fail_alloc=false;short_payload=true;
 assert(zen_load_title_pcm(encoded.data(),encoded.size(),&out)==-1 && !out.pcm && allocations.empty() && live_files==0);
 std::remove(cache_path.c_str());
 puts("PASS real title PCM loader + actual media_decode: exact bytes, 32-byte alignment, no runtime synth on hit, reuse, fallback dispatch, original other-audio dispatch, header/payload/truncation/size/short-read/OOM/cleanup");
}
