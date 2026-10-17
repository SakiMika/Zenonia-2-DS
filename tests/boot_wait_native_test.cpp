#include "../source/zen_native_boot.cpp"
#include <cassert>
#include <vector>
#include <cstdio>
uint32_t zen_boot_clock_ms(void) { return 123; }
static bool no_address=false;
void *lgt_translate_ptr(const LgtLoadedImage *im,uint32_t a) {
    if(no_address || a<im->text_old || a-im->text_old>=im->text_size) return nullptr;
    return im->text+a-im->text_old;
}
int main() {
    std::vector<uint8_t> text(0x8b538,0xa5);
    LgtLoadedImage im{};im.text=text.data();im.text_old=0x1000;im.text_size=text.size();
    auto p=text.data()+0x5a3fc-0x1000;
    const uint8_t original[]={0x00,0xb5,0x83,0x6a,0x01,0x33,0x83,0x62,
        0x32,0x2b,0x01,0xdd,0xff,0xf7,0x9a,0xff,0x00,0x20,0x02,0xbc,0x08,0x47};
    memcpy(p,original,sizeof(original));
    const uint32_t slots[]={0x87640u,0x87650u,0x87670u};
    const uint32_t targets[]={0x5a3fcu,0x5a4a8u,0x5a634u};
    for(unsigned i=0;i<3;++i) {
        const uint32_t v=(uint32_t)(uintptr_t)(text.data()+targets[i]-0x1000)|1u;
        memcpy(text.data()+slots[i]-0x1000,&v,4);
    }
    const auto before=text;
    assert(!zen_native_boot_install(nullptr));
    no_address=true;assert(!zen_native_boot_install(&im));no_address=false;
    --im.text_size;assert(!zen_native_boot_install(&im));++im.text_size;
    for(unsigned i=0;i<sizeof(original);++i) {
        p[i]^=1;const auto bad=text;
        assert(!zen_native_boot_install(&im) && text==bad);p[i]^=1;
    }
    for(auto a:slots) {
        uint8_t *q=text.data()+a-0x1000;*q^=1;const auto bad=text;
        assert(!zen_native_boot_install(&im) && text==bad);*q^=1;
    }
    assert(text==before && zen_native_boot_install(&im));
    unsigned changes=0;
    for(size_t i=0;i<text.size();++i) if(text[i]!=before[i]) {
        const bool cmp=i==0x5a404-0x1000;
        bool slot=false;for(auto a:slots) if(i>=a-0x1000 && i<a-0x1000+4) slot=true;
        assert(cmp || slot);if(cmp) assert(text[i]==16);++changes;
    }
    assert(changes>=1 && changes<=13 && ZenBootProfile::trace.hooks);
    const auto patched=text;
    assert(!zen_native_boot_install(&im) && text==patched);
    puts("PASS guarded boot installer: only wait immediate and three private callback slots changed; all22 signature mismatches/null/size fail closed, repeated install leaves code unchanged");
}
