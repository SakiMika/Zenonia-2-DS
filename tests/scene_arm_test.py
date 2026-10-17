"""Native ARM coordinate smoke tests, not a DS ROM or pixel-render test.
Install requirements.txt, then: python tests/title_arm_test.py
"""
import os,sys,struct
if os.getenv('ZEN_RE_TOOLS'):sys.path.insert(0,os.environ['ZEN_RE_TOOLS'])
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
root=Path(__file__).resolve().parents[1]
u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
with (root/'zenonia2nds/binary.mod').open('rb') as f:
 e=ELFFile(f)
 for name in ['.text','.data','.bss']:
  s=e.get_section_by_name(name);a=s['sh_addr'];n=s['sh_size']
  u.mem_map(a&~4095,((n+(a&4095)+4095)//4096)*4096)
  if name!='.bss':u.mem_write(a,s.data())
u.mem_map(0x2000000,0x100000);u.mem_map(0x3000000,0x100000);u.mem_map(0x4000000,4096)
R=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def rr(i):return u.reg_read(R[i])
def w(a,v):u.mem_write(a,struct.pack('<I',v))
def ret(v=0):u.reg_write(R[0],v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
def text(p):
 b=bytearray()
 while True:
  c=bytes(u.mem_read(p+len(b),1))
  if c==b'\0':return bytes(b)
  b+=c

# Execute real native handlers 14/15/18 and the complete scroll routine 1ce94.
# Final font rasterizer and external services are stubs; native clip setter runs.
SELF,CMD,ARGS,RESOURCE,MAN,GFX,APP,TXT=range(0x2008000,0x2008800,0x100)
clips=[];draws=[];bars=[];actual_clips=[];stops=set()
def hook(uc,a,n,d):
 if a in stops:uc.emu_stop();return
 if a==0x690cc:ret(TXT)
 elif a==0x1400ccc:ret((rr(0)<<16)|(rr(1)<<8)|rr(2))
 elif a==0x1400e3c:ret(256)
 elif a==0xe618:ret()
 elif a==0x102ac:ret(0) # background pixel sampling
 elif a==0x1214:ret(0x2005000)
 elif a==0x140097c:
  p,q,z=rr(0),rr(1),rr(2);u.mem_write(p,bytes(u.mem_read(q,z)));ret(p)
 elif a==0xdc90:
  if rr(1):clips.append(struct.unpack('<4h',u.mem_read(rr(1),8)))
  # Continue through the real native clip setter, not a stub.
 elif a==0x10b6c:
  actual_clips.append(struct.unpack('<4h',u.mem_read(GFX+0x38,8)))
  draws.append((rr(2),rr(3),struct.unpack('<5I',u.mem_read(u.reg_read(UC_ARM_REG_SP),20))))
  ret(4) # four lines of synthetic font output, fixed wrapping
 elif a==0xde38:ret(11)
 elif a==0xde20:ret(2)
 elif a==0x58e40:bars.append((rr(0),rr(1),rr(2),rr(3)));ret()
 elif a in [0x70fd0,0x70f70,0x70f3c]:ret()
u.hook_add(UC_HOOK_CODE,hook)
def run(a):
 stops.clear();stops.add(0x4000000)
 u.reg_write(UC_ARM_REG_SP,0x30ff000);u.reg_write(UC_ARM_REG_LR,0x4000000)
 u.reg_write(R[0],SELF);u.reg_write(R[1],CMD)
 try:u.emu_start(a|1,0x4000000,count=100000)
 except Exception:
  print('PC',hex(u.reg_read(UC_ARM_REG_PC)),'regs',[hex(rr(i)) for i in range(4)]);raise
 assert u.reg_read(UC_ARM_REG_PC)==0x4000000
 return rr(0)
w(CMD+8,ARGS);w(CMD+16,0x1234);w(SELF+20,RESOURCE)
w(RESOURCE+16,MAN);w(MAN+16,0) # no reset loop needed for coordinate-storage test
u.mem_write(TXT,b'opening narration\0')
for fn,op in [(0x69ecc,14),(0x69f2c,15)]:
 for y in [110,58]:
  vals=[0x1000a,0,120,y]
  for i,v in enumerate(vals):w(ARGS+12*i+4,v)
  w(CMD,op);run(fn)
  assert struct.unpack('<3I',u.mem_read(SELF+28,12))==(0,120,y)
print('PASS real native handlers14/15 store unchanged X120 + image anchor Y110 ->58')
w(0x1400070,0x2001000);w(0x2001008,0x2001100)
w(0x1400074,0x2002000);w(0x2002004,0)
w(0x14000f0,APP);w(APP+12,1);w(APP+16,GFX)
w(GFX+0x40,256);w(GFX+0x44,192)
for original_y,original_h in [(200,30),(185,80)]:
 thresholds=[]
 for patched in [False,True]:
  y=108 if patched else original_y;h=80 if patched else original_h
  vals=[y,170,h,0x10000,255,255,255,1]
  for i,v in enumerate(vals):w(ARGS+i*12+4,v)
  w(CMD,18);threshold=h+4*13;thresholds.append(threshold)
  for scroll in [0,1,40,threshold,threshold+1]:
   w(0x157dad8,scroll);clips.clear();draws.clear();bars.clear();actual_clips.clear()
   result=run(0x6af60)
   assert clips==[(43,y,170,h)],clips
   assert draws==[(43,y+h-scroll,(170,0xffffffff,0xffffffff,0,1))],draws
   assert result==(0x1234 if scroll>threshold else CMD),(scroll,result)
   counter=struct.unpack('<I',u.mem_read(0x157dad8,4))[0]
   assert counter==(0 if scroll>threshold else scroll+1)
   if patched:
    assert 0<=y and y+h<=192
    assert actual_clips==[(43,108,170,80)],actual_clips
  # Mode2 is an existing speed choice: keep exactly +2 px/tick.
  w(ARGS+7*12+4,2);w(0x157dad8,0);run(0x6af60)
  assert struct.unpack('<I',u.mem_read(0x157dad8,4))[0]==2
 assert thresholds==([82,132] if original_h==30 else [132,132])
print('PASS real native opcode18 + scroll1ce94: clip Y108 H80 ends188; first panels gain50px scroll travel; long panels retain80px; native end condition follows new height; speed1/2 unchanged; font width/style unchanged')
print('LIMIT: font rasterizer/external services stubbed, fixed four-line font output; not a ROM or visual test')
