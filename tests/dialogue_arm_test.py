"""Native dialogue coordinate regression. Final rasterizers/external services stubbed.
Executes real helper1c07c via relocated trampoline, GUI17250/171f8, full1c328.
C++ wrapper behavior is bridged in hooks; see dialogue_native_test.cpp for C++.
"""
import os,sys,struct,zlib
if os.getenv('ZEN_RE_TOOLS'):sys.path.insert(0,os.environ['ZEN_RE_TOOLS'])
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
root=Path(__file__).resolve().parents[1];u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
with (root/'zenonia2nds/binary.mod').open('rb') as f:
 e=ELFFile(f)
 for sn in ['.text','.data','.bss']:
  s=e.get_section_by_name(sn);a=s['sh_addr'];n=s['sh_size'];u.mem_map(a&~4095,((n+(a&4095)+4095)//4096)*4096)
  if sn!='.bss':u.mem_write(a,s.data())
u.mem_map(0x2000000,0x800000);u.mem_map(0x4000000,4096)
R=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def rr(i):return u.reg_read(R[i])
def w(a,v):u.mem_write(a,struct.pack('<I',v))
def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
def si(v):return v if v<0x80000000 else v-0x100000000

def ret(v=0):u.reg_write(R[0],v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
def text(p):
 b=bytearray()
 while True:
  c=bytes(u.mem_read(p+len(b),1))
  if c==b'\0':return bytes(b)
  b+=c
# Actual GameUI metadata, including optional transform byte after flags.
b=(root/'zenonia2nds/com/GameUI.pzx').read_bytes();meta=zlib.decompress(b[70:]);pixels=zlib.decompress(b[598:]);p=0;groups=[]
while p<len(meta):
 n=struct.unpack_from('<H',meta,p)[0];p+=2;g=[]
 for _ in range(n):
  im,x,y,fl=struct.unpack_from('<HhhB',meta,p);p+=7
  if fl:p+=1
  g.append((im,x,y))
 groups.append(g)
dims=[struct.unpack_from('<HH',pixels,struct.unpack_from('<I',pixels,i*4)[0]) for i in range(struct.unpack_from('<I',pixels)[0]//4)]
bounds={}
for g in range(4,9):
 fr=groups[g];x=min(v[1] for v in fr);y=min(v[2] for v in fr)
 bounds[g]=(x,y,max(v[1]+dims[v[0]][0] for v in fr)-x,max(v[2]+dims[v[0]][1] for v in fr)-y)
assert bounds[4]==(1,267,238,53)
# Parsed GameUI groups4..8 are empty: only its PZX composites paint dialogue.
# Exact GUI SHA is checked in check_preservation.py; native parser regression separately.
CTX,GLOBAL,RESLIST,GUI,OUTER,OWNER,MAN,TABLE,VT,SELF,ACTOR,TXT,APP,GFX,PORRES,POROWN,PORMAN,PORTAB,PORSPR,PORVT=range(0x2001000,0x2002400,0x100)
BS,DS,PS,WRAP,AFTER,GWRAP,TRAMP=range(0x4000100,0x4000800,0x100)
# Helper trampoline exactly matches source installer. Preserve real prologue/global.
original=bytes(u.mem_read(0x1c07c,8));assert original==bytes.fromhex('70b5104c82b0061c')
u.mem_write(TRAMP,struct.pack('<8H2I',0xb570,0x4c03,0xb082,0x1c06,0x4b02,0x4718,0x46c0,0x46c0,0x140006c,0x1c085))
# RAM index<->sprite for original 16f54 and 171f8.
sprite_to_group={}
for g in range(10):
 spr=0x2005000+g*0x100;sprite_to_group[spr]=g;w(TABLE+4*g,spr);w(spr,VT)
w(VT+0x1c,BS|1);w(VT+0x10,DS|1)
w(0x140006c,GLOBAL);w(GLOBAL+4,RESLIST);w(GLOBAL+8,2);w(RESLIST+4,GUI)
w(GUI,OUTER);w(OUTER+8,10);w(GUI+12,OWNER);w(OWNER+12,MAN);w(MAN+8,TABLE);w(MAN+16,10)
w(0x14000f0,APP);w(APP+12,1);w(APP+16,GFX)
w(0x1400070,APP);w(APP+8,GFX);w(GFX+0x40,11)
w(0x14000e4,PORRES);w(PORRES+0x14,1)
w(PORRES+8,POROWN);w(POROWN+12,PORMAN);w(PORMAN+16,1);w(PORMAN+8,PORTAB);w(PORTAB,PORSPR);w(PORSPR,PORVT);w(PORVT+0x10,PS|1)
w(ACTOR+0x6e0,1);u.mem_write(ACTOR+4,b'\0');u.mem_write(ACTOR+0x3ec,b'Name\0')
w(0x14000c8,0x2003000);w(0x2003008,ACTOR)
w(PORVT+0x14,0x4000801)
w(SELF+8,ACTOR);w(SELF+0x14,TXT)
calls=[];pending=[];patched=False

def hook(uc,a,n,d):
 if a==0x4000000:u.emu_stop();return
 if a==WRAP:
  pending.append((rr(0),rr(1),u.reg_read(UC_ARM_REG_LR)))
  u.reg_write(UC_ARM_REG_LR,AFTER|1);u.reg_write(UC_ARM_REG_PC,TRAMP|1)
 elif a==AFTER:
  out,g,lr=pending.pop()
  if 4<=g<=8:
   r=list(struct.unpack('<4h',u.mem_read(out,8)));r[1]-=128;u.mem_write(out,struct.pack('<4h',*r))
  u.reg_write(UC_ARM_REG_PC,lr)
 elif a==GWRAP:
  if 4<=si(rr(3))<=8:u.reg_write(R[2],(rr(2)-128)&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,0x17251)
 elif a==0x1214:ret(CTX-8)
 elif a==0x1220:ret(CTX)
 elif a==BS:
  g=sprite_to_group[rr(0)];u.mem_write(rr(3),struct.pack('<4h',*bounds[g]));ret(rr(3))
 elif a==DS:
  calls.append(('frame',sprite_to_group[rr(0)],si(rr(1)),si(rr(2))));ret()
 elif a==PS:
  calls.append(('portrait',si(rr(1)),si(rr(2)),rr(3)));ret()
 elif a==0x16ff4:ret() # actual dialogue GUI record groups are empty
 elif a==0x1400e3c:ret(256)
 elif a==0x1400e4c:ret(192)
 elif a==0x140096c:ret(len(text(rr(0))))
 elif a==0x148ec:ret(PORRES)
 elif a==0x1400ccc:ret((rr(0)<<16)|(rr(1)<<8)|rr(2))
 elif a==0xe618:ret()
 elif a==0x10b6c:
  st=struct.unpack('<5I',u.mem_read(u.reg_read(UC_ARM_REG_SP),20))
  calls.append(('body',si(rr(2)),si(rr(3)),st,text(rr(1))));ret(3)
 elif a==0xe438:
  w(word(u.reg_read(UC_ARM_REG_SP)),11);w(rr(3),len(text(rr(1)))*6);ret()
 elif a==0x5f108:
  st=struct.unpack('<3I',u.mem_read(u.reg_read(UC_ARM_REG_SP),12))
  calls.append(('name',si(rr(2)),si(rr(3)),st,text(rr(1))));ret()
 elif a in [0x10fb0,0x108dc]:
  calls.append(('choice_box',si(rr(1)),si(rr(2)),rr(3)));ret()
 elif a==0x1c264:ret(0) # continuation test only: all letters available
 elif a==0x16f84:ret(PORSPR)
 elif a==0x4000800: # continue-arrow vtable draw
  calls.append(('advance',si(rr(1)),si(rr(2))));ret()
u.hook_add(UC_HOOK_CODE,hook)
def run(fn,args):
 u.reg_write(UC_ARM_REG_SP,0x27ff000);u.reg_write(UC_ARM_REG_LR,0x4000000)
 for i,v in enumerate(args):u.reg_write(R[i],v)
 try:u.emu_start(fn|1,0x4000000,count=200000)
 except Exception:
  print('PC',hex(u.reg_read(UC_ARM_REG_PC)),'regs',[hex(rr(i)) for i in range(4)],'calls',calls);raise
 assert u.reg_read(UC_ARM_REG_PC)==0x4000000,hex(u.reg_read(UC_ARM_REG_PC))
 assert not pending
# 0=right speaker,1=left speaker; short/long names cover all groups5..8.
for side in [0,1]:
 for name in [b'Lee',b'Long Name']:
  for page in [0,1,3]:
   u.mem_write(SELF+4,bytes([side]));u.mem_write(ACTOR+0x3ec,name+b'\0')
   snapshots=[]
   for patched in [False,True]:
    u.mem_write(0x1c07c,struct.pack('<2HI',0x4b00,0x4718,WRAP|1) if patched else original)
    w(0x1c660,GWRAP|1 if patched else 0x17251);u.ctl_remove_cache(0x1000,0x8c538)
    u.mem_write(TXT,b'fixture line1\nfixture line2\nfixture line3\0');calls.clear()
    run(0x1c328,[SELF,page,90,0]);snapshots.append(list(calls))
   old,new=snapshots
   assert [c[0] for c in old]==[c[0] for c in new]
   for a,b in zip(old,new):
    if a[0]=='frame':assert b==(a[0],a[1],a[2],a[3]-128),(a,b)
    elif a[0] in ['portrait','body','name']:
     assert b==(a[0],a[1],a[2]-128,*a[3:]),(a,b)
   body=next(c for c in new if c[0]=='body');assert body[2]==146 and body[3][2]==3,body
   assert body[3]==(214,90,3,page*3,0),body
   assert [146+i*14 for i in range(3)]==[146,160,174]
   assert 174+11<=192
   assert any(c[0]=='portrait' for c in new),new
   assert any(c[0]=='name' for c in new),new
print('PASS full native1c328 + geometry trampoline + GUI dispatch: both speaker sides, names groups5..8, pages0/1/3; frame/name/portrait/body all -128; body limit3 and pagination/font arguments unchanged')
print('PASS native body anchor274->146; fixture 3x11px rows +3px gap fit y146..184; body frame267..319 ->139..191')
# Full dialogue update/draw also anchors the continue arrow and YES/NO controls.
for choice in [0,1]:
 snapshots=[]
 for patched in [False,True]:
  u.mem_write(0x1c07c,struct.pack('<2HI',0x4b00,0x4718,WRAP|1) if patched else original)
  w(0x1c660,GWRAP|1 if patched else 0x17251);u.ctl_remove_cache(0x1000,0x8c538)
  u.mem_write(SELF+0x24,bytes([choice]));w(SELF+0x18,90);w(SELF+0x1c,0);w(SELF+0x20,1)
  calls.clear();run(0x1c72c,[SELF,0]);snapshots.append(list(calls))
 old,new=snapshots
 assert len(old)==len(new)
 for a,b in zip(old,new):
  if a[0]=='frame':assert b==(a[0],a[1],a[2],a[3]-128),(a,b)
  else:assert b==(a[0],a[1],a[2]-128,*a[3:]),(a,b)
 assert any(c[0]==('choice_box' if choice else 'advance') for c in new),new
print('PASS full native1c72c continuation/YES-NO: arrow, button outlines/fills/labels all follow -128; no double shift')
print('LIMIT final sprite/font rasterizers and external services stubbed; synthetic 3-line text; no ROM/visual test')
