// Host filesystem/IO fault stubs. Compile the actual asset implementation
// and extracted WIPI resource entry points, not a reimplementation.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <cassert>
#include <string>
#include <vector>
#include <filesystem>
#include <fstream>
static size_t reads=0, payload=0, live=0;
static bool short_read=false, bad_seek=false, bad_tell=false, bad_rewind=false;
static FILE *observed_open(const char *p,const char *mode) {
    std::string path=p;
    if(path.rfind("fat:/zenonia2nds/",0)==0) path="zenonia2nds/"+path.substr(17);
    FILE *f=fopen(path.c_str(),mode); if(f) ++live; return f;
}
static int observed_close(FILE *f) { assert(live); --live; return fclose(f); }
static int observed_seek(FILE *f,long offset,int origin) {
    if((bad_seek && origin==SEEK_END)||(bad_rewind && origin==SEEK_SET)) return -1;
    return fseek(f,offset,origin);
}
static long observed_tell(FILE *f) { return bad_tell ? -1 : ftell(f); }
static size_t observed_read(void *dst,size_t size,size_t n,FILE *f) {
    ++reads;
    const size_t got=fread(dst,size,short_read && n ? n-1 : n,f);
    payload+=got*size; return got;
}
#define fopen observed_open
#define fclose observed_close
#define fseek observed_seek
#define ftell observed_tell
#define fread observed_read
#include "../source/embedded_assets.cpp"
#undef fopen
#undef fclose
#undef fseek
#undef ftell
#undef fread
static char handle_buffer[256]; // -no-pie puts this below 2GB, like ARM RAM.
static void *handle_malloc(size_t n) { return n<=sizeof(handle_buffer) ? handle_buffer : nullptr; }
static unsigned audio_notes=0;
static void audio_note_asset(const char *) { ++audio_notes; }
#include "../source/zen_boot_profile.h"
uint32_t zen_boot_clock_ms(void) { return 0; }
#define malloc handle_malloc
#include "resource_entry_points.inc"
#undef malloc
static void reset() { assert(live==0); reads=payload=0; }
int main() {
    assert(embedded_assets_init());
    size_t files=0,total=0;
    for(const auto &e:std::filesystem::recursive_directory_iterator("zenonia2nds")) {
        if(!e.is_regular_file()) continue;
        const std::string name=std::filesystem::relative(e.path(),"zenonia2nds").generic_string();
        std::ifstream f(e.path(),std::ios::binary);
        std::vector<char> expected((std::istreambuf_iterator<char>(f)),{});
        std::vector<char> actual(expected.size()+2,0x5a);
        reset(); uint32_t size=0;
        const int id=knl_get_resource_id(name.c_str(),&size);
        assert(id>0 && size==expected.size() && payload==0 && reads==0);
        assert(knl_get_resource(id,actual.data()+1,size)==0);
        assert(reads==(size ? 1u : 0u) && payload==size && live==0);
        assert(actual.front()==0x5a && actual.back()==0x5a);
        assert(!size || memcmp(expected.data(),actual.data()+1,size)==0);
        ++files;total+=size;
    }
    // Retained transient-view API also still works, without sharing caller buffers.
    reset(); EmbeddedAssetView view{};
    assert(embedded_asset_find("menu/logo.pzx",&view) && view.size>0);
    std::vector<uint8_t> saved(view.data,view.data+view.size),dst(view.size+8,0xa5);
    const uint8_t *view_ptr=view.data;
    assert(embedded_asset_size("menu/logo.pzx",nullptr));
    assert(embedded_asset_read("/menu/logo.pzx",dst.data(),dst.size())==0);
    assert(memcmp(view_ptr,saved.data(),saved.size())==0);
    embedded_asset_release_cache();
    reset();
    assert(embedded_asset_read("menu/logo.pzx",dst.data(),1)==-18 && reads==0);
    assert(embedded_asset_read("menu/logo.pzx",nullptr,100)==-9);
    assert(embedded_asset_read("missing.file",dst.data(),dst.size())==-12);
    uint32_t size=123;
    assert(!embedded_asset_size("missing.file",&size) && size==0);
    assert(!embedded_asset_size(nullptr,&size) && size==0);
    assert(!embedded_asset_size("",&size));
    assert(!embedded_asset_size(std::string(200,'a').c_str(),&size));
    assert(knl_get_resource(-1,dst.data(),dst.size())==-9);
    assert(knl_get_resource(1,nullptr,0)==-9);
    assert(knl_get_resource_id(nullptr,&size)==-12 && size==0);
    for(int i=0;i<4;++i) {
        short_read=i==0; bad_seek=i==1; bad_tell=i==2; bad_rewind=i==3;
        assert(embedded_asset_read("menu/logo.pzx",dst.data(),dst.size())==-12 && live==0);
    }
    short_read=bad_seek=bad_tell=bad_rewind=false;
    // Temporary zero-byte asset exercises the successful no-fread path.
    { FILE *f=fopen("zenonia2nds/.resource-zero-test","wb");assert(f);fclose(f); }
    reset();
    assert(embedded_asset_size(".resource-zero-test",&size) && size==0);
    assert(embedded_asset_read(".resource-zero-test",dst.data(),0)==0 && reads==0);
    std::filesystem::remove("zenonia2nds/.resource-zero-test");
    assert(live==0 && audio_notes==files);
    printf("PASS actual resource-ID + direct read: %zu files, %zu bytes, size lookup reads zero payload; read exactly once/file; bytes/guards/errors/cleanup/cache API verified\n",files,total);
}
