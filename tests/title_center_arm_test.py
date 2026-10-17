"""v047: real title call sites/animation and GUI dispatcher, native menu
foreground and native raster. External final sprites/text are stubs except
for the separate pixel-span test at the end. No full ROM screenshot claim.
"""
from pathlib import Path
import struct
root=Path(__file__).resolve().parents[1]
s=(root/'tests/title_labels_arm_test.py').read_text()
exec(compile(s[:s.index('# Verify the actual resource')],str(root/'tests/title_labels_arm_test.py'),'exec'))
# Tail wrappers equivalent to C++: +8 X; existing Y shifts unchanged.
# Save r3/mode, target in ip; restore stack before native tail call.
def wrapper(y,target):
 return struct.pack('<8HI',0xb408,0x4b03,0x469c,0xbc08,0x3108,0x3a00+y,0x4760,0x46c0,target|1)
u.mem_write(WRAP,wrapper(96,0x17250));ANIMWRAP=WRAP+0x100
u.mem_write(ANIMWRAP,wrapper(64,0x70e84))
# Original animation call sites and actual renderer; only virtual final sprite
# draws are stubbed by this harness. ANIM reuses a fresh area, not GUI objects.
ANIM,STATE,FRAME,ASPR,AVT=range(0x200e000,0x200e500,0x100)
w(ANIM+8,STATE);w(ANIM+16,FRAME);w(FRAME,ASPR);w(ASPR,AVT);w(AVT+16,0x4000101)
for p in [0x5a908,0x5b3ec]:w(p,ANIMWRAP|1)
for entry,stop in [(0x5a680,0x5a692),(0x5a6c0,0x5a6d2),(0x5b37c,0x5b38e),(0x5b3b0,0x5b3c2)]:
 for x in [0,64,120,239]:
  for y in [0,64,192,264,319]:
   calls.clear();u.mem_write(FRAME+4,struct.pack('<hh',x,y));u.reg_write(R[0],0);u.reg_write(UC_ARM_REG_R5,ANIM)
   run(entry,stop)
   assert calls==[('label',x+8,(y-64)&0xffffffff,0)],(hex(entry),calls)
print('PASS four real title intro/menu call sites + animation renderer: X+8, Y-64, mode preserved')
# GUI blink label receives the same horizontal canvas shift.
w(0x140006c,0x200d000);w(0x200509c,4);w(0x5a030,WRAP|1)
calls.clear();run(0x59fd0)
assert [c for c in calls if c[0]=='label']==[('label',8,(-96)&0xffffffff,0)],calls
assert ('records',(-96)&0xffffffff,1) in calls # records are also shifted by native dispatcher
print('PASS real blink/GUI dispatch: authored title sprites receive X+8, Y-96; blink logic unchanged')
# Selected foreground text is ALREADY centered using native screen width256.
# Do not shift it by8 again or change its font/width/formatting.
w(0x1400070,0x2001000);w(0x2001008,0x2001100);w(0x2001100,0x2001200);w(0x2001200,0)
w(SELF+0x30,1);w(SELF+0x34,0);w(SELF+0x2c,1)
u.mem_write(FRAG+48+6,struct.pack('<h',264));u.mem_write(0x5b476,struct.pack('<H',0x3b6a))
expected=text(0x1400768+10);assert expected==b'New Game',expected
snap=[]
for patched in [False,True]:
 w(0x5b534,WRAP|1 if patched else 0x17251);u.ctl_remove_cache(0x5b3f4,0x5b55c)
 w(0x2001140,11);u.reg_write(R[0],SELF);calls.clear();run(0x5b3f4)
 drawn=[c for c in calls if c[0]=='menu'];assert len(drawn)==2 and all(expected in c[3] for c in drawn),drawn
 assert [c[1] for c in drawn]==[1,0] and all(c[4]==(256,0xffffffff,0xffffffff,0,1) for c in drawn),drawn
 snap.append(drawn)
assert snap[0]==snap[1]
print('PASS real English New Game foreground: shadow/face X, Y, width256, format/font unchanged; no double center shift')
# Native static copyright already computes (256-imageWidth)/2; retain that path.
WIDTHFN,HEIGHTFN=0x4000220,0x4000240
OWNER2,HOLDER2,TABLE2=0x200e600,0x200e700,0x200e800
w(OWNER2+8,HOLDER2);w(HOLDER2+8,TABLE2);w(TABLE2,ASPR)
w(AVT+0x1c,WIDTHFN|1);w(AVT+0x20,HEIGHTFN|1);w(AVT+0x14,0x4000101)
def logo_metrics(uc,a,n,d):
 if a==WIDTHFN:ret(112)
 elif a==HEIGHTFN:ret(60)
 elif a==0x1400e4c:ret(192)
u.hook_add(UC_HOOK_CODE,logo_metrics)
LOGO_TRAMP=WRAP+0x200;expected=bytes.fromhex('3368041c1b6a301c')
assert bytes(u.mem_read(0x5a744,8))==expected
u.mem_write(LOGO_TRAMP,expected+struct.pack('<4HI',0x3c20,0x4a01,0x4710,0x46c0,0x5a74d))
u.mem_write(0x5a744,struct.pack('<2HI',0x4a00,0x4710,LOGO_TRAMP|1))
u.reg_write(UC_ARM_REG_R7,OWNER2);calls.clear();run(0x5a712,0x5a76a)
assert calls==[('label',72,100,0)],calls
print('PASS actual copyright centering: width112 -> X72, copyright Y100 (+32); no extra+8 applied')
# Native pixel writer proof: a240px panel at X8 has8px margin on both sides.
s=(root/'tests/hud_pixel_arm_test.py').read_text()
g={"__file__":str(root/'tests/hud_pixel_arm_test.py')}
exec(compile(s[:s.index('p,ys=run(128,132)')],g['__file__'],'exec'),g)
fn=s[s.index('def run(offset,y):'):s.index('p,ys=run(128,132)')].replace('def run(offset,y):','def centered_run(offset,y):').replace('zip(regs,[0,y,240,60])','zip(regs,[8,y,240,60])')
exec(fn,g);p,ys=g['centered_run'](0,64)
assert ys==set(range(64,124)) and sum(v!=0 for v in p)==240*60
for y in range(400):
 for x in range(256):assert p[y*256+x]==(0xf800 if 64<=y<124 and 8<=x<248 else 0),(x,y)
print('PASS original ARM raster: X8..247 (240px), symmetric8px margins; pixel size/rows unchanged')
