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

calls=[];stops=set();font_height=11
GUI,OUTER,OWNER,MAN,TABLE,SPRITE,VT,FRAG=range(0x200a000,0x200a800,0x100)
SELF=0x200b000
WRAP=0x200c000
# Tail wrapper equivalent to the C++ wrapper: preserve group and stack args.
u.mem_write(WRAP,bytes.fromhex('08b4024b9c4608bc603a6047')+struct.pack('<I',0x17251))
def hook(uc,a,n,d):
 if a in stops:uc.emu_stop();return
 if a==0x1214:ret(0x2005000)
 elif a==0x16ff4:
  calls.append(('records',rr(2),rr(3)));ret()
 elif a==0x4000100:
  calls.append(('label',rr(1),rr(2),rr(3)));ret()
 elif a==0x17350:ret()
 elif a==0x17360:ret(GUI)
 elif a==0x16f54:ret(SPRITE)
 elif a==0x1400e3c:ret(256)
 elif a==0x81354:
  u.mem_write(rr(0),bytes([rr(1)&255])*rr(2));ret(rr(0))
 elif a==0x14009dc:
  fmt=text(rr(1)); value=text(rr(2)); assert b'%s' in fmt
  u.mem_write(rr(0),fmt.replace(b'%s',value)+b'\0');ret()
 elif a==0x10b6c:
  sp=u.reg_read(UC_ARM_REG_SP)
  args=struct.unpack('<5I',u.mem_read(sp,20))
  calls.append(('menu',rr(2),rr(3),text(rr(1)),args));ret()
 else:return
u.hook_add(UC_HOOK_CODE,hook)
def run(a,stop=0x4000000):
 stops.clear();stops.add(stop)
 u.reg_write(UC_ARM_REG_SP,0x30ff000);u.reg_write(UC_ARM_REG_LR,0x4000000)
 try:u.emu_start(a|1,stop,count=100000)
 except Exception:
  print('PC',hex(u.reg_read(UC_ARM_REG_PC)),'REGS',[hex(rr(i)) for i in range(4)],'calls',calls);raise
 assert u.reg_read(UC_ARM_REG_PC)==stop,hex(u.reg_read(UC_ARM_REG_PC))
w(GUI,OUTER);w(OUTER+8,40);w(GUI+12,OWNER)
w(OWNER+12,MAN);w(MAN+16,13);w(MAN+8,TABLE)
for i in range(13):w(TABLE+i*4,SPRITE)
w(SPRITE,VT);w(VT+16,0x4000101);w(SPRITE+8,FRAG)
# Verify the actual resource, rather than assigning a guessed label to BG frames.
import zlib
raw=(root/'zenonia2nds/menu/Title.pzx')
if not raw.exists():raw=next((root/'zenonia2nds').rglob('Title.pzx'))
b=raw.read_bytes();streams=[]
for i in range(len(b)-2):
 if b[i]==0x78:
  try: streams.append(zlib.decompress(b[i:]))
  except zlib.error:pass
meta=next(x for x in streams if len(x)==723)
assert struct.unpack_from('<5H',meta)==(0,1,14,64,265)
# Run the actual blink callback, through native 17250 -> 171f8 -> virtual label draw.
w(0x140006c,0x200d000);w(0x200509c,4)
for patched in [False,True]:
 w(0x5a030,WRAP|1 if patched else 0x17251)
 u.ctl_remove_cache(0x59fd0,0x5a034)
 calls.clear();run(0x59fd0)
 label=[c for c in calls if c[0]=='label'];assert len(label)==1,calls
 offset=label[0][2];offset=offset if offset<0x80000000 else offset-0x100000000
 assert 265+offset==(169 if patched else 265),(patched,calls)
 assert ('records',offset&0xffffffff,1) in calls
w(0x200509c,0);calls.clear();run(0x59fd0)
assert not calls, calls
w(0x200509c,4)
print('PASS native blink callback + GUI dispatch: Title.pzx group1 image14 anchor y265 ->169; blink behavior unchanged')
# Actual full menu foreground, actual Korean New game string and original formatter.
# Stub final text rasterizer only. Model font metrics separately from screen height.
w(0x1400070,0x2001000);w(0x2001008,0x2001100)
w(0x2001100,0x2001200);w(0x2001200,0)
w(SELF+0x30,1);w(SELF+0x34,0);w(SELF+0x2c,1) # native menu option index 1
u.mem_write(FRAG+48+6,struct.pack('<h',264))
# Final font rasterizer at 10b6c is stubbed, its native caller is not.
baseline=None
for patched in [False,True]:
 w(0x5b534,WRAP|1 if patched else 0x17251)
 u.mem_write(0x5b476,struct.pack('<H',0x3b6a if patched else 0x3b0a))
 u.ctl_remove_cache(0x5b3f4,0x5b55c)
 for fh in [11,13,16]:
  font_height=fh;w(0x2001140,fh)
  u.reg_write(R[0],SELF);calls.clear();run(0x5b3f4)
  drawn=[c for c in calls if c[0]=='menu'];assert len(drawn)==2,calls
  expected=264-(fh-14)-10-(96 if patched else 0)
  assert all(c[2]==expected for c in drawn) and [c[1] for c in drawn]==[1,0],drawn
  assert all(b'\xbb\xf5\xb7\xce\xc7\xcf\xb1\xe2' in c[3] for c in drawn),drawn
  assert all(c[4]==(256,0xffffffff,0xffffffff,0,1) for c in drawn),drawn
  assert any(c[0]=='label' and c[2]==((-96 if patched else 0)&0xffffffff) for c in calls)
print('PASS full native menu foreground: Korean New game shadow+face y257 ->161 at metric11; metrics13/16 also shift exactly -96; all font/style arguments unchanged')
print('LIMIT: final sprite/font rasterizers stubbed; no compiled ROM / emulator visual verification')
