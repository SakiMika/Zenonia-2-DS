#pragma once
#include <stdint.h>
#include <stdio.h>
#include <string.h>
// Real tick time (not the game's scaled clock); supplied by the runner.
uint32_t zen_boot_clock_ms(void);
namespace ZenBootProfile {
enum Kind { Timer,Paint,Resource,Audio,KindCount };
struct Metric { uint32_t calls=0,total=0,max=0; };
struct Trace {
 bool active=true,hooks=false,rating=false,auth=false,title=false;
 uint32_t rating_at=0,transition_at=0,rating_exit=0,auth_at=0,title_at=0,title_end=0;
 uint32_t rating_calls=0,auth_calls=0,title_calls=0,last_counter=0;
 uint32_t pcm_hits=0,pcm_misses=0;
 Metric cost[KindCount]{};
 char slow_resource[32]{};
};
inline Trace trace{};
inline void reset() { const bool h=trace.hooks;trace=Trace{};trace.hooks=h; }
inline void add(Kind k,uint32_t begin,const char *name=nullptr) {
 if(!trace.active) return;
 const uint32_t elapsed=zen_boot_clock_ms()-begin;
 Metric &m=trace.cost[k];++m.calls;m.total+=elapsed;
 if(elapsed>m.max) {
  m.max=elapsed;
  if(k==Resource && name) { strncpy(trace.slow_resource,name,31);trace.slow_resource[31]=0; }
 }
}
inline void phase(unsigned p,uint32_t counter=0) {
 if(!trace.active) return;
 const uint32_t t=zen_boot_clock_ms();
 if(p==3) { if(!trace.rating) trace.rating_at=t;trace.rating=true;++trace.rating_calls;trace.last_counter=counter; }
 if(p==4) { if(!trace.auth) trace.auth_at=t;trace.auth=true;++trace.auth_calls; }
 if(p==5) { if(!trace.title) trace.title_at=t;trace.title=true;++trace.title_calls; }
}
inline void line(int i,char *out,unsigned cap) {
 const Trace &t=trace;
 if(i==0) snprintf(out,cap,"BOOT051 DIAG hooks:%s",t.hooks?"OK":"FAIL");
 else if(i==1) snprintf(out,cap,"rating:%s n%lu c%lu",t.rating?"YES":"NO",(unsigned long)t.rating_calls,(unsigned long)t.last_counter);
 else if(i==2) snprintf(out,cap,"rating wait %s%lums",t.transition_at?"":"?",(unsigned long)(t.transition_at?t.transition_at-t.rating_at:0));
 else if(i==3) snprintf(out,cap,"next init %s%lums",t.rating_exit&&t.transition_at?"":"?",(unsigned long)(t.rating_exit&&t.transition_at?t.rating_exit-t.transition_at:0));
 else if(i==4) snprintf(out,cap,"rating->title %s%lums",t.rating&&t.title?"":"?",(unsigned long)(t.rating&&t.title?t.title_at-t.rating_at:0));
 else if(i==5) snprintf(out,cap,"auth:n%lu title:n%lu",(unsigned long)t.auth_calls,(unsigned long)t.title_calls);
 else if(i==6) snprintf(out,cap,"first title draw:%lums",(unsigned long)(t.title_end?t.title_end-t.title_at:0));
 else if(i>=7 && i<11) {
  static const char *names[]={"timer","paint","resource","audio"};const int k=i-7;
  snprintf(out,cap,"%s max%lu sum%lu",names[k],(unsigned long)t.cost[k].max,(unsigned long)t.cost[k].total);
 } else if(i==11) snprintf(out,cap,"slow:%s",t.slow_resource[0]?t.slow_resource:"none >=1ms");
 else snprintf(out,cap,"PCM051 hit%lu miss%lu",(unsigned long)t.pcm_hits,(unsigned long)t.pcm_misses);
}
}
