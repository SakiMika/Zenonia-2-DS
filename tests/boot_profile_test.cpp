#include "../source/zen_boot_profile.h"
#include <cassert>
#include <string>
static uint32_t clock_ms=0;
uint32_t zen_boot_clock_ms(void) { return clock_ms; }
int main() {
 using namespace ZenBootProfile;
 trace.hooks=true;reset();assert(trace.hooks && trace.active);
 char row[32];line(0,row,32);assert(std::string(row)=="BOOT051 DIAG hooks:OK");
 line(4,row,32);assert(std::string(row).find('?')!=std::string::npos);
 clock_ms=100;phase(3,0);clock_ms=500;phase(3,16);trace.transition_at=500;
 clock_ms=700;trace.rating_exit=700;phase(4);clock_ms=8100;phase(5);
 clock_ms=8150;trace.title_end=8150;
 line(2,row,32);assert(std::string(row)=="rating wait 400ms");
 line(3,row,32);assert(std::string(row)=="next init 200ms");
 line(4,row,32);assert(std::string(row)=="rating->title 8000ms");
 line(6,row,32);assert(std::string(row)=="first title draw:50ms");
 add(Resource,8100,"menu/logo.pzx");assert(trace.cost[Resource].max==50);
 clock_ms=8160;add(Resource,8150,"short");assert(trace.cost[Resource].calls==2 && trace.cost[Resource].total==60);
 assert(std::string(trace.slow_resource)=="menu/logo.pzx");
 clock_ms=20;add(Paint,0xfffffff0u);assert(trace.cost[Paint].total==36);
 auto frozen=trace;trace.active=false;clock_ms=9999;phase(3,50);add(Audio,10);
 assert(trace.rating_calls==frozen.rating_calls && trace.cost[Audio].calls==0);
 for(int i=0;i<13;++i) { char guards[34];memset(guards,0x5a,sizeof guards);line(i,guards+1,32);assert(guards[0]==0x5a && guards[33]==0x5a && strlen(guards+1)<=31); }
 puts("PASS diagnostic profile: real-tick deltas, unknown phases, categories, max asset, wraparound, freeze, 32-char rows");
}
