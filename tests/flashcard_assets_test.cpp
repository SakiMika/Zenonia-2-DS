#include "embedded_assets.h"
#include "zen_predecoded_audio.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <unistd.h>
namespace fs=std::filesystem;
static void put(const fs::path &p,const std::vector<unsigned char>&data) {
 fs::create_directories(p.parent_path());std::ofstream f(p,std::ios::binary);f.write((const char*)data.data(),data.size());assert(f.good());
}
static std::vector<unsigned char> read(const fs::path &p) {
 std::ifstream f(p,std::ios::binary);return {(std::istreambuf_iterator<char>(f)),{}};
}
int main() {
 const auto before=fs::current_path();char name[]="/tmp/wipi-fat-XXXXXX";assert(mkdtemp(name));fs::current_path(name);
 char path[192];EmbeddedAssetView view{};uint32_t size=0;
 assert(!embedded_asset_path("binary.mod",path,sizeof path));
 assert(!embedded_asset_find("binary.mod",&view));
 fs::path fat="fat:/zenonia2nds",sd="sd:/zenonia2nds";
 put(fat/"binary.mod",{'f','a','t'});put(sd/"binary.mod",{'s','d'});
 std::vector<unsigned char> data(8193);for(unsigned i=0;i<data.size();++i)data[i]=(i*31)^0xa5;
 put(fat/"data/test.zt1",data);put(fat/"empty",{});put(sd/"sd-only",{42});
 assert(embedded_assets_init());assert(std::string(embedded_asset_root())=="fat:/zenonia2nds/");
 assert(embedded_asset_path("/data/test.zt1",path,sizeof path));assert(std::string(path)=="fat:/zenonia2nds/data/test.zt1");
 assert(embedded_asset_path("data\\test.zt1",path,sizeof path));
 for(const char *bad:{"../secret","data/../secret","./binary.mod","data/./x","fat:/binary.mod","data//x","data/","","/","\\..\\secret","data/\nsecret"})assert(!embedded_asset_path(bad,path,sizeof path));
 std::string longname(200,'x');assert(!embedded_asset_path(longname.c_str(),path,sizeof path));
 char tiny[4];assert(!embedded_asset_path("binary.mod",tiny,sizeof tiny) && tiny[0]==0);
 assert(embedded_asset_size("data/test.zt1",&size) && size==data.size());
 std::vector<unsigned char> buffer(data.size()+2,0x77);assert(embedded_asset_read("data/test.zt1",buffer.data()+1,data.size())==0);
 assert(buffer.front()==0x77 && buffer.back()==0x77 && !memcmp(buffer.data()+1,data.data(),data.size()));
 assert(embedded_asset_read("data/test.zt1",buffer.data(),1)==-18);
 assert(embedded_asset_read("data/test.zt1",nullptr,data.size())==-9);
 assert(embedded_asset_read("missing",buffer.data(),buffer.size())==-12);
 assert(!embedded_asset_find("sd-only",&view)); // never mix devices
 assert(embedded_asset_find("data/test.zt1",&view));assert(view.size==data.size() && !memcmp(view.data,data.data(),data.size()));embedded_asset_release_cache();
 assert(embedded_asset_size("empty",&size) && size==0);assert(embedded_asset_read("empty",buffer.data(),0)==0);
 // Exercise the REAL optional PCM loader through the external FAT root.
 const char *fixture=getenv("ZEN_TEST_FIXTURE");
 if(fixture && fs::is_regular_file(fs::path(fixture)/"runner_audio/title108.zpc")) {
  auto encoded=read(fs::path(fixture)/"sound/108.mmf");auto packed=read(fs::path(fixture)/"runner_audio/title108.zpc");
  put(fat/"runner_audio/title108.zpc",packed);ZenDecodedPcm pcm{};
  assert(zen_load_title_pcm(encoded.data(),encoded.size(),&pcm)==1 && pcm.samples==431010 && pcm.rate==8000);
  assert(!memcmp(pcm.pcm,packed.data()+32,pcm.samples*2));free(pcm.pcm);
  fs::remove(fat/"runner_audio/title108.zpc");assert(zen_load_title_pcm(encoded.data(),encoded.size(),&pcm)==-1 && !pcm.pcm);
  puts("PASS optional PCM cache: real file loaded from selected FAT folder; missing-cache fallback preserved");
 } else puts("SKIP optional PCM fixture (set ZEN_TEST_FIXTURE)");
 fs::rename("fat:","fat-off");assert(embedded_assets_init());assert(std::string(embedded_asset_root())=="sd:/zenonia2nds/");
 assert(embedded_asset_find("binary.mod",&view) && view.size==2);embedded_asset_release_cache();
 fs::remove_all("sd:");
 if(!fs::exists("/zenonia2nds/binary.mod"))assert(!embedded_assets_init());
 fs::current_path(before);fs::remove_all(name);
 puts("PASS external-folder assets: root priority, no volume mixing, confined paths, metadata/direct/cache reads, guards/errors, missing game");
}
