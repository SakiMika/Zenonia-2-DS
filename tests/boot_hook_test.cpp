#include "../source/zen_native_boot.cpp"
#include <cassert>
#include <sys/mman.h>
static uint32_t clock_ms=100,seen_self=0;
uint32_t zen_boot_clock_ms(void) { return clock_ms; }
void *lgt_translate_ptr(const LgtLoadedImage*,uint32_t) { return nullptr; }
static uint32_t mock_rating(uint32_t self) {
 seen_self=self;uint32_t *p=(uint32_t*)(uintptr_t)self;
 ++p[10];if(p[10]>16) { p[2]=4;clock_ms+=500; }return 123;
}
static uint32_t mock_auth(uint32_t self) { seen_self=self;clock_ms+=20;return 234; }
static uint32_t mock_title(uint32_t self) { seen_self=self;clock_ms+=30;return 345; }
int main() {
 void *p=mmap((void*)0x02000000,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
 assert(p==(void*)0x02000000);const uint32_t self=0x02000000;
 rating_update=mock_rating;auth_update=mock_auth;title_draw=mock_title;
 ZenBootProfile::reset();
 for(unsigned i=0;i<17;++i) { assert(traced_rating(self)==123 && seen_self==self);clock_ms+=10; }
 const auto &t=ZenBootProfile::trace;
 assert(t.rating_calls==17 && t.last_counter==16 && t.rating_at==100);
 assert(t.transition_at==260 && t.rating_exit==760);
 assert(traced_auth(self)==234 && t.auth_at==770 && seen_self==self);
 assert(traced_title(self)==345 && t.title_at==790 && t.title_end==820 && seen_self==self);
 clock_ms+=10;assert(traced_title(self)==345 && t.title_end==820 && t.title_calls==2);
 ZenBootProfile::trace.active=false;
 assert(traced_auth(self)==234 && traced_title(self)==345 && t.auth_calls==1 && t.title_calls==2);
 munmap(p,4096);
 puts("PASS compiled phase hooks: original self/results preserved; wait vs next-init timestamps; first-title draw timing; freeze does not suppress native callbacks");
}
