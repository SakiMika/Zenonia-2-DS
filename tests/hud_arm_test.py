"""Real GUI parser + HUD dispatcher2033c, portrait1f5a0, icons200a4,
GUI172c4/17250/16ff4/171f8. Final rasterizers/stat services stubbed.
C++ hook behavior bridged in Unicorn; hud_native_test.cpp tests actual C++.
"""
import os,sys,struct,zlib
from pathlib import Path
if os.getenv('ZEN_RE_TOOLS'):sys.path.insert(0,os.environ['ZEN_RE_TOOLS'])
root=Path(__file__).resolve().parents[1]
# Reuse exact native parser harness, retaining parsed GUI object/vtables in RAM.
path=root/'tests/native_gui_arm_test.py';src=path.read_text();src=src[:src.index("if '--trampoline' in sys.argv:\n    # Exercise")]
sys.argv=[str(path),str(root/'zenonia2nds/com/GameUI.gui')]
exec(compile(src,str(path),'exec'))
# Replace parser hook only after real resource parsing has completed.
from unicorn.arm_const import *
# Existing parser hook ignores most native addresses, but rejects imports.
# A single combined hook suppresses it in draw phase.
# Unicorn doesn't expose hook handles from the reused harness. Recreate U from
# its mapped RAM snapshot, so no parser-only hook survives into draw execution.
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
old=U;U=Uc(UC_ARCH_ARM,UC_MODE_ARM)
for lo,hi,perms in old.mem_regions():
 U.mem_map(lo,hi-lo+1,perms);U.mem_write(lo,bytes(old.mem_read(lo,hi-lo+1)))
def w(a,v):U.mem_write(a,struct.pack('<I',v))
def word(a):return struct.unpack('<I',U.mem_read(a,4))[0]
def si(v):return v if v<0x80000000 else v-0x100000000
def ret(v=0):U.reg_write(regs[0],v);U.reg_write(UC_ARM_REG_PC,U.reg_read(UC_ARM_REG_LR))
CTX,GFX,APP,RES,RESTAB,OWNER,MAN,TAB,VT,ACTOR,SELF,IMG,IMVT=range(0x2020000,0x2020d00,0x100)
DRAW=0x4000100;PIC=0x4000200;WRAP=0x4000300;TAIL=0x4000400;AFTER=0x4000500
TRAMP=0x2070000;TTRAMP=TRAMP+32
# Real native prologues, relocated exactly as installer does.
assert bytes(U.mem_read(0x2033c,8))==bytes.fromhex('f0b53e4c8db00121')
assert bytes(U.mem_read(0x1e9f4,8))==bytes.fromhex('f0b5384a8eb08018')
U.mem_write(TRAMP,struct.pack('<8H2I',0xb5f0,0x4c03,0xb08d,0x2101,0x4b02,0x4718,0x46c0,0x46c0,0x140006c,0x20345))
U.mem_write(TTRAMP,struct.pack('<8H2I',0xb5f0,0x4a03,0xb08e,0x1880,0x4b02,0x4718,0x46c0,0x46c0,0x4fb,0x1e9fd))
U.mem_write(0x2033c,struct.pack('<2HI',0x4b00,0x4718,WRAP|1))
U.mem_write(0x1e9f4,struct.pack('<2HI',0x4b00,0x4718,TAIL|1))
w(0x140006c,RES);w(RES+4,RESTAB);w(RES+8,2);w(RESTAB+4,OBJ)
w(OBJ+12,OWNER);w(OWNER+12,MAN);w(MAN+8,TAB);w(MAN+16,10)
b=(root/'zenonia2nds/com/GameUI.pzx').read_bytes();meta=zlib.decompress(b[70:]);pos=0;groups=[]
for g in range(10):
 n=struct.unpack_from('<H',meta,pos)[0];pos+=2;fr=[]
 for j in range(n):
  im,x,y,flags=struct.unpack_from('<HhhB',meta,pos);pos+=7
  if flags:pos+=1
  fr.append((im,x,y))
 groups.append(fr)
 spr=0x2030000+g*0x200;w(TAB+4*g,spr);w(spr,VT);w(spr+8,spr+0x20)
 U.mem_write(spr+12,bytes([n]))
 for j,(im,x,y) in enumerate(fr):
  p=spr+0x20+24*j;w(p,IMG);U.mem_write(p+4,struct.pack('<hh',x,y))
w(VT+0x10,DRAW|1);w(IMG,IMVT);w(IMVT+0x14,PIC|1)
w(0x1400070,APP);w(APP+8,GFX);w(GFX+0x40,11)
w(0x14000c8,APP);w(APP+8,ACTOR); # same app global normally points another object
# Reassign font-global to an independent root, keeping font height11.
FONTROOT=0x2021000;w(0x1400070,FONTROOT);w(FONTROOT+8,GFX)
w(ACTOR+0x6e0,1)
# Virtual clock/status draw services not exercised; tail entry still runs real trampoline.
# Initial loader effect v034, then wrapper applies additional64 temporarily.
for item in allgroups[2]:
 p=item['ptr'];U.mem_write(p+10,struct.pack('<h',item['rect'][1]-64))
calls=[];active=False;pending=[];saved=0
shifts=[]
rect_by_ptr={it['ptr']:i for i,it in enumerate(allgroups[2])}
sprite_by_ptr={word(TAB+g*4):g for g in range(10)}
def end():
 global active
 if not active:return
 for it in allgroups[2]:
  p=it['ptr'];y=struct.unpack('<h',U.mem_read(p+10,2))[0];U.mem_write(p+10,struct.pack('<h',y+64))
 for address,y in shifts:U.mem_write(address,struct.pack('<h',y))
 shifts.clear();active=False

def draw_hook(u,a,n,d):
 global active,saved
 if a==0x4000000:U.emu_stop()
 elif a==WRAP:
  assert not active;active=True;saved=word(CTX+0x40)
  for g in [1,2,3,9]:
   spr=word(TAB+4*g)
   for j in range(len(groups[g])):
    address=spr+0x20+j*24+6
    y=struct.unpack('<h',U.mem_read(address,2))[0]
    shifts.append((address,y));U.mem_write(address,struct.pack('<h',y-128))
  for it in allgroups[2]:
   p=it['ptr'];y=struct.unpack('<h',U.mem_read(p+10,2))[0];U.mem_write(p+10,struct.pack('<h',y-64))
  pending.append(U.reg_read(UC_ARM_REG_LR));U.reg_write(UC_ARM_REG_LR,AFTER|1);U.reg_write(UC_ARM_REG_PC,TRAMP|1)
 elif a==AFTER:
  end();U.reg_write(UC_ARM_REG_PC,pending.pop())
 elif a==TAIL:
  end();calls.append(('top_tail',active,rr(0)));U.reg_write(UC_ARM_REG_PC,TTRAMP|1)
 elif a==0x1e9fc:
  # Real displaced prologue must have added4fb to original SELF.
  assert rr(0)==SELF+0x4fb and not active
  # Let real tail early-return on flag !=0; no expensive clock backend fixture.
 elif a==0x1e858:
  calls.append(('top_status',active));ret()
 elif a==0x1220:ret(CTX)
 elif a==0x1214:ret(CTX-8)
 elif a==0x1f6ec:ret() # toggles group3 visibility from game state; fixture leaves2 visible
 elif a==0x1ebe4:
  ys=[struct.unpack('<h',U.mem_read(it['ptr']+10,2))[0] for it in allgroups[2]]
  calls.append(('stats',active,ys[:3]));ret()
 elif a==0x36d40:ret(0)
 elif a==0x1400ccc:ret(0xffff)
 elif a in [0x81354,0x140099c]:
  U.mem_write(rr(0),bytes([rr(1)&255])*rr(2));ret(rr(0))
 elif a==0x14009dc:
  U.mem_write(rr(0),b'01\0');ret(2)
 elif a==0x5f578:
  calls.append(('label',active,si(rr(2)),si(rr(3))));ret()
 elif a in [0x77cac,0x77d48,0x77dd4,0x78814]:
  it=rr(0);x,y,ww,hh=struct.unpack('<4h',U.mem_read(it+8,8))
  calls.append(('gui',active,rect_by_ptr.get(it,-1),x+si(rr(2)),y+si(rr(3)),ww,hh));ret()
 elif a==DRAW:
  g=sprite_by_ptr[rr(0)]
  for j,(im,_,_) in enumerate(groups[g]):
   x,y=struct.unpack('<hh',U.mem_read(rr(0)+0x20+j*24+4,4))
   calls.append(('sprite',active,g,im,x+si(rr(1)),y+si(rr(2))))
  ret()
 elif a==PIC:
  calls.append(('portrait',active,si(rr(1)),si(rr(2))));ret()
U.hook_add(UC_HOOK_CODE,draw_hook)
U.mem_write(SELF+0x4fb,b'\1') # clock tail early-return fixture
# Group2 visible only; resource native flags are at OBJ+4.
flags=word(OBJ+4);U.mem_write(flags,bytes([0,0,1,0,0,0,0,0,0,0]))
for repeat in range(3):
 calls.clear();U.reg_write(UC_ARM_REG_SP,0x30ff000);U.reg_write(UC_ARM_REG_LR,0x4000000);U.reg_write(regs[0],SELF)
 try:U.emu_start(0x2033d,0x4000000,count=300000)
 except Exception:
  print('PC',hex(U.reg_read(UC_ARM_REG_PC)),'registers',[hex(rr(i)) for i in range(4)],'calls',calls[-12:]);raise
 assert U.reg_read(UC_ARM_REG_PC)==0x4000000
 assert not active and not pending and word(CTX+0x40)==0 and word(GFX+0x40)==11
 rects=[v for v in calls if v[0]=='gui'];assert len(rects)==11,rects
 assert [r[4] for r in rects]==[r['rect'][1]-128 for r in allgroups[2]]
 assert all(r[1] for r in rects)
 bg=[c for c in calls if c[0]=='sprite' and c[2]==2 and c[3]==0];assert bg==[('sprite',True,2,0,0,132)],bg
 por=[c for c in calls if c[0]=='portrait'];assert por and por[0][3]==groups[1][1][2]-128,por
 assert sum(c[0]=='label' and c[1] for c in calls)>=5,calls
 assert ('top_status',False) in calls and any(c[0]=='top_tail' and not c[1] for c in calls)
print('PASS real native2033c + relocated prologues, portrait1f5a0, quickslot200a4, GUI dispatch: HUD geometry scope on TOP, BG y132, 11 rects -128, labels follow rects, geometry restored before clock/status; 3 repeats no drift, raster origin unchanged')
print('LIMIT: synthetic PZX objects populated from real metadata; final rasterizers, HP/MP stat helper and external services stubbed; no ROM/visual validation')
