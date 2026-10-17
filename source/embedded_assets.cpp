#include "embedded_assets.h"
#include "runner_package_config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace {
static uint8_t *g_cache=nullptr;
static size_t g_cache_cap=0;

static char g_root[48]{};
}

const char *embedded_asset_root(void) { return g_root; }

bool embedded_asset_path(const char *name,char *out,size_t cap) {
    if(!out || !cap) return false;
    out[0]=0;
    if(!name || !g_root[0]) return false;
    while(*name=='/' || *name=='\\') ++name;
    if(!*name) return false;
    char relative[144];size_t length=0,segment=0;
    for(const unsigned char *p=(const unsigned char*)name;;++p) {
        unsigned char c=*p;
        if(c=='\\') c='/';
        if(c==0 || c=='/') {
            const size_t part=length-segment;
            if(!part || (part==1 && relative[segment]=='.') ||
               (part==2 && relative[segment]=='.' && relative[segment+1]=='.')) return false;
            if(!c) break;
            segment=length+1;
        } else if(c<32 || c==127 || c==':') return false;
        if(length+1>=sizeof(relative)) return false;
        relative[length++]=(char)c;
    }
    relative[length]=0;
    const int n=snprintf(out,cap,"%s%s",g_root,relative);
    if(n<=0 || (size_t)n>=cap) { out[0]=0;return false; }
    return true;
}

bool embedded_assets_init(void) {
    embedded_asset_release_cache();g_root[0]=0;
    // Pick one device once. Never fall back to another card for individual
    // missing assets, which could mix resources from different game versions.
    const char *roots[]={"fat:/" RUNNER_GAME_DIRECTORY "/",
                         "sd:/" RUNNER_GAME_DIRECTORY "/",
                         "/" RUNNER_GAME_DIRECTORY "/"};
    for(const char *root:roots) {
        char path[96];snprintf(path,sizeof(path),"%sbinary.mod",root);
        FILE *f=fopen(path,"rb");
        if(!f) continue;
        const bool ok=fseek(f,0,SEEK_END)==0 && ftell(f)>0;
        fclose(f);
        if(ok) { snprintf(g_root,sizeof(g_root),"%s",root);return true; }
    }
    return false;
}

// Keep the transient-view API unchanged for audio/database/ELF callers.
// Resource-ID lookup must NOT load the payload just to discover its size.
static FILE *open_sized_asset(const char *name, uint32_t *size) {
    char path[192];
    if(!embedded_asset_path(name,path,sizeof(path))) return nullptr;
    FILE *f=fopen(path,"rb");
    if(!f) return nullptr;
    if(fseek(f,0,SEEK_END)!=0) { fclose(f); return nullptr; }
    const long end=ftell(f);
    if(end<0 || (unsigned long)end>0x7fffffc0UL) { fclose(f); return nullptr; }
    *size=(uint32_t)end;
    return f;
}

bool embedded_asset_size(const char *name, uint32_t *out_size) {
    if(out_size) *out_size=0;
    uint32_t size=0;
    FILE *f=open_sized_asset(name,&size);
    if(!f) return false;
    fclose(f);
    if(out_size) *out_size=size;
    return true;
}

int embedded_asset_read(const char *name, void *dst, uint32_t cap) {
    if(!dst) return -9;
    uint32_t size=0;
    FILE *f=open_sized_asset(name,&size);
    if(!f) return -12;
    if(size>cap) { fclose(f); return -18; }
    if(fseek(f,0,SEEK_SET)!=0) { fclose(f); return -12; }
    const bool ok=!size || fread(dst,1,size,f)==size;
    fclose(f);
    return ok ? 0 : -12;
}

bool embedded_asset_find(const char *name, EmbeddedAssetView *out) {
    if(out) { out->data=nullptr; out->size=0; }
    char path[192];
    if(!embedded_asset_path(name,path,sizeof(path))) return false;
    FILE *f=fopen(path,"rb");
    if(!f) return false;
    if(fseek(f,0,SEEK_END)!=0) { fclose(f); return false; }
    long end=ftell(f);
    if(end<0 || (unsigned long)end>0x7fffffc0UL) { fclose(f); return false; }
    rewind(f);
    const size_t need=(size_t)end;
    if(need>g_cache_cap) {
        size_t cap=(need+31u)&~31u;
        uint8_t *p=(uint8_t*)realloc(g_cache,cap?cap:32);
        if(!p) { fclose(f); return false; }
        g_cache=p; g_cache_cap=cap;
    }
    if(need && fread(g_cache,1,need,f)!=need) { fclose(f); return false; }
    fclose(f);
    if(out) { out->data=g_cache; out->size=(uint32_t)need; }
    return true;
}

void embedded_asset_release_cache(void) {
    free(g_cache); g_cache=nullptr; g_cache_cap=0;
}

