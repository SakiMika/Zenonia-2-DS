"""Run the real rating update and drawing functions. External framebuffer/
image services and the expensive next-state init are stubs, not a full ROM.
"""
from pathlib import Path
import struct,re
root=Path(__file__).resolve().parents[1]
s=(root/'tests/title_labels_arm_test.py').read_text()
exec(compile(s[:s.index('# Verify the actual resource')],str(root/'tests/title_labels_arm_test.py'),'exec'))
# Match native installer guard to actual ELF instructions.
code=(root/'source/zen_native_boot.cpp').read_text()
raw=code.split('const uint8_t expected[]={',1)[1].split('};',1)[0]
expected=bytes(int(v,16) for v in re.findall(r'0x([0-9a-f]+)',raw))
assert bytes(u.mem_read(0x5a3fc,len(expected)))==expected
assert struct.unpack('<I',u.mem_read(0x87640,4))[0]==0x5a3fd # state3 update
assert struct.unpack('<I',u.mem_read(0x87648,4))[0]==0x5a245 # state3 draw
header=(root/'source/zen_native_boot.h').read_text()
limit=int(re.search(r'ZEN_RATING_LAST_TICK=(\d+)',header)[1]);assert limit==16
# Actual private rating draw's resource chain and image virtual methods.
GAME,HANDLER,MAN2,HOLDER,SPR2,VT2=range(0x200e000,0x200e600,0x100)
w(0x14000e4,GAME);w(GAME+0x18,HANDLER);w(HANDLER+0x10,MAN2)
w(MAN2+0x34,HOLDER);w(HOLDER+8,0x200e600);w(0x200e608,0x200e700);w(0x200e708,TABLE);w(TABLE,SPR2);w(SPR2,VT2)
w(VT2+0x1c,0x4000221);w(VT2+0x20,0x4000241);w(VT2+0x14,0x4000261)
w(0x1400070,0x2001000);w(0x2001008,0x2001100);w(0x2001100,0x2001200)
events=[]
def boot_hook(uc,a,n,d):
 if a==0x5a340:
  # Stub full next-state init: verify native call uses original self, and
  # state3 has not been skipped directly to title.
  assert rr(0)==SELF
  events.append(('init',struct.unpack('<I',u.mem_read(SELF+0x28,4))[0]));ret()
 elif a==0x1400e4c:ret(192)
 elif a==0x1400ccc:ret(0xffff)
 elif a==0x1046c:ret() # white background
 elif a==0x4000220:ret(80)
 elif a==0x4000240:ret(96)
 elif a==0x4000260:
  sp=u.reg_read(UC_ARM_REG_SP)
  events.append(('draw',rr(3),struct.unpack('<I',u.mem_read(sp,4))[0]));ret()
u.hook_add(UC_HOOK_CODE,boot_hook)
results=[]
for threshold in [50,limit]:
 u.mem_write(0x5a404,struct.pack('<H',0x2b00|threshold));u.ctl_remove_cache(0x5a3fc,0x5a412)
 w(SELF+0x28,0);events.clear()
 for tick in range(1,100):
  u.reg_write(R[0],SELF);run(0x5a3fc)
  assert rr(0)==0
  if events and events[-1][0]=='init':break
  u.reg_write(R[0],SELF);run(0x5a244)
 assert tick==threshold+1 and events[-1]==('init',tick),(tick,events)
 draws=[x for x in events if x[0]=='draw']
 # counter1..15 uses clamped fade alpha; frame16 uses full-opaque mode0.
 assert draws[0]==('draw',1,0) and draws[14]==('draw',1,10),draws
 assert draws[15]==('draw',0,0),draws
 results.append((tick,draws))
assert results[1][1]==results[0][1][:16]
print('PASS real state3 update: original transitions51 -> patched17; one native state4-init call with original self; first16 rating draws/fade unchanged, including full-opacity frame16')
