#include "hud_backend_stub.h"
// Host test: real com/000.mls -> 12-byte native argument records -> wrappers.
#include "../source/zen_native_layout.cpp"
#include <sys/mman.h>
#include <assert.h>
#include <fstream>
#include <vector>
#include <array>
void *lgt_translate_ptr(const LgtLoadedImage*,uint32_t){return nullptr;}
static std::vector<uint32_t> seen;
static uint32_t callback(uint32_t self,uint32_t cmd,uint32_t flags) {
    assert(self==0x12345678 && flags==0xabcdef);
    uint32_t *c=(uint32_t*)(uintptr_t)cmd,*a=(uint32_t*)(uintptr_t)c[2];
    seen.clear();for(unsigned i=0;i<c[1];i++)seen.push_back(a[i*3+1]);
    return 0x98765432;
}
int main() {
    void *base=mmap((void*)0x02000000,0x10000,PROT_READ|PROT_WRITE,
      MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
    assert(base==(void*)0x02000000);
    original_scene_image=original_scene_animation=original_scene_text=callback;
    std::ifstream in("zenonia2nds/script/com/000.mls",std::ios::binary);
    std::vector<char> raw((std::istreambuf_iterator<char>(in)),{});assert(raw.size()==1308);
    std::vector<uint32_t> words(raw.size()/4);memcpy(words.data(),raw.data(),raw.size());
    uint32_t *c=(uint32_t*)base,*a=c+32;unsigned pos=1,images=0,texts=0;
    for(unsigned row=0;row<words[0];row++) {
        uint32_t op=words[pos++],n=words[pos++];std::vector<uint32_t> original;
        c[0]=op;c[1]=n;c[2]=(uint32_t)(uintptr_t)a;
        for(unsigned j=0;j<n;j++) {
            a[j*3]=words[pos++];a[j*3+1]=words[pos++];a[j*3+2]=0xfeed;
            original.push_back(a[j*3+1]);
        }
        if(op!=14 && op!=15 && op!=18)continue;
        ScriptOpFn f=op==18?zen_scene_text:(op==15?zen_scene_animation:zen_scene_image);
        for(unsigned repeat=0;repeat<40;repeat++) {
            assert(f(0x12345678,(uint32_t)(uintptr_t)c,0xabcdef)==0x98765432);
            auto expected=original;
            if(op==18){expected[0]=108;expected[2]=80;}
            else expected[3]=58;
            assert(seen==expected);
            for(unsigned j=0;j<n;j++)assert(a[j*3+1]==original[j] && a[j*3+2]==0xfeed);
        }
        if(op==18)texts++;else images++;
        // Wrong resource/text reference/geometry must pass straight through.
        unsigned j=op==18?3:0;uint32_t saved=a[j*3+1];a[j*3+1]=0x2000a;
        f(0x12345678,(uint32_t)(uintptr_t)c,0xabcdef);
        assert(seen[op==18?0:3]==original[op==18?0:3]);a[j*3+1]=saved;
    }
    assert(pos==words.size() && images==9 && texts==8);
    puts("PASS 9 real opening picture commands +8 narration commands; repeat-safe restoration; resource scoping; strings/RGB/speed/flags unchanged");
}
