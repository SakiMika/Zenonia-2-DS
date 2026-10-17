import sys,struct,json
# capstone is not required; only unicorn and pyelftools.
import os
if os.environ.get('ZEN_RE_TOOLS'): sys.path.insert(0,os.environ['ZEN_RE_TOOLS'])
from unicorn import *
from unicorn.arm_const import *
from pathlib import Path
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[1] if 'tests' in str(Path(__file__)) else Path('/data/zenonia-review/zenonia2-dsi-main')
U=Uc(UC_ARCH_ARM,UC_MODE_ARM); f=(ROOT/'zenonia2nds/binary.mod').open('rb'); e=ELFFile(f)
for name in ['.text','.data','.bss']:
 s=e.get_section_by_name(name); a=s['sh_addr']; n=s['sh_size']; U.mem_map(a&~4095,((n+(a&4095)+4095)//4096)*4096)
 if name!='.bss':U.mem_write(a,s.data())
U.mem_map(0x2000000,0x800000);U.mem_map(0x3000000,0x100000);U.mem_map(0x4000000,4096)
def word(a):return struct.unpack('<I',U.mem_read(a,4))[0]
heap=0x2010000; records=[]; current=-1; SRC=0x2000000
imports={}
for sec in ['.text','.data']:
 ss=e.get_section_by_name(sec);bb=ss.data()
 for o in range(0,len(bb)-16,4):
  w=struct.unpack_from('<4I',bb,o)
  if w[0]==0xe52de004 and w[1]>>24==0xeb: imports[ss['sh_addr']+o]=(w[2],w[3])
regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def rr(i):return U.reg_read(regs[i])
def ret(v):U.reg_write(UC_ARM_REG_R0,v);U.reg_write(UC_ARM_REG_PC,U.reg_read(UC_ARM_REG_LR))
def hook(u,a,n,data):
 global heap,current
 if a in imports and a not in [0x140097c,0x81314,0x140099c,0x81354]:
  t,i=imports[a]
  if t==1 and i==0x405:
   p,q=rr(0),rr(1);bb=bytearray()
   while True:
    v=U.mem_read(q+len(bb),1)[0];bb.append(v)
    if not v:break
   U.mem_write(p,bytes(bb));ret(p)
  elif t==0x1fb and i==0x33:ret(256)
  elif t==0x1fb and i==0x34:ret(192)
  elif t==0x1fb and i==0xdf:ret(((rr(0)>>3)<<11)|((rr(1)>>2)<<5)|(rr(2)>>3))
  else: raise RuntimeError('Unhandled import '+hex(a)+' '+str((t,i)))
 elif a==0x6cfa8:
  U.mem_write(rr(1),struct.pack('<I',len(b)));ret(SRC)
 elif a==0x6d00c:ret(0)
 elif a==0x1220:ret(0x2009000)
 elif a in [0xa33c,0xa34c]:
  p=heap;heap+=(rr(0)+15)&~15;ret(p)
 elif a in [0x140097c,0x81314]:
  p,q,z=rr(0),rr(1),rr(2); U.mem_write(p,bytes(U.mem_read(q,z)));ret(p)
 elif a in [0x140099c,0x81354]:
  p,v,z=rr(0),rr(1),rr(2);U.mem_write(p,bytes([v&255])*z);ret(p)
 elif a==0x178b2:
  current=U.reg_read(UC_ARM_REG_R5)-SRC;records.append({'offset':current,'type':U.mem_read(SRC+current,1)[0]})
 elif a==0x179d4: pass
 elif a==0x179c0:
  records[-1]['object']=word(U.reg_read(UC_ARM_REG_SP)+16)
 elif a==0x17a14:
  pass
 elif a==0x4000000:U.emu_stop()
U.hook_add(UC_HOOK_CODE,hook)
b=Path(sys.argv[1]).read_bytes(); U.mem_write(SRC,b);OBJ=0x2008000
U.reg_write(UC_ARM_REG_SP,0x30ff000);U.reg_write(UC_ARM_REG_LR,0x4000000);U.reg_write(UC_ARM_REG_R0,OBJ);U.reg_write(UC_ARM_REG_R1,SRC);U.reg_write(UC_ARM_REG_R2,0)
entry=0x17839
if '--trampoline' in sys.argv:
 tramp=0x2070000
 expected=bytes.fromhex('70b581b0081c1b4b')
 assert bytes(U.mem_read(0x17a68,8))==expected
 bb=expected[:6]+struct.pack('<5H',0x4b02,0x4c02,0x4720,0x46c0,0x46c0)+struct.pack('<2I',0x6cfa9,0x17a71)
 U.mem_write(tramp,bb)
 U.reg_write(UC_ARM_REG_R1,0x200a000)
 U.mem_write(0x200a000,b'com/GameUI.gui\0')
 entry=tramp|1
try:U.emu_start(entry,0x4000000,count=2000000)
except UcError as ex:print('ERROR',ex,hex(U.reg_read(UC_ARM_REG_PC)));raise
if '--trampoline' in sys.argv: OBJ=rr(0)
print('RETURN',rr(0),'groups',len(records),'heap',hex(heap));print('obj',U.mem_read(OBJ,16).hex())
# Capture objects from nested group table.
def word(a):return struct.unpack('<I',U.mem_read(a,4))[0]
outer=word(OBJ);count=word(outer+8);table=word(outer+4);allgroups=[]
for i in range(count):
 g=word(table+4*i);cnt=word(g+8);tab=word(g+4);items=[]
 for j in range(cnt):
  p=word(tab+4*j);raw=bytes(U.mem_read(p,16));items.append({'ptr':p,'type':raw[5],'rect':list(struct.unpack_from('<4h',raw,8))})
 allgroups.append(items)
print('PASS native parser: groups=',len(allgroups),'elements=',sum(map(len,allgroups)))
if '--trampoline' in sys.argv:
 assert len(allgroups)==10 and len(allgroups[2])==11
 assert [x['rect'][1] for x in allgroups[2]]==[289,296,318,303,303,303,303,300,275,315,291]
 print('PASS relocated Thumb trampoline: GUI loader returned expected 11 original HUD rects')
if '--json' in sys.argv:
 dest=Path(sys.argv[sys.argv.index('--json')+1]);dest.write_text(json.dumps({'records':records,'groups':allgroups},indent=2))

if '--trampoline' in sys.argv:
    # Exercise the real guest layout helper and clip reset, not a pixel mock.
    U.mem_write(0x1400070,struct.pack('<I',0x200b000))
    U.mem_write(0x200b008,struct.pack('<I',0x200b100))
    U.mem_write(0x200b100,struct.pack('<I',0))
    U.mem_write(OBJ+8,struct.pack('<I',2))
    def call(fn,args):
        U.reg_write(UC_ARM_REG_SP,0x30ff000)
        U.reg_write(UC_ARM_REG_LR,0x4000000)
        for i,v in enumerate(args):U.reg_write(regs[i],v)
        U.emu_start(fn|1,0x4000000,count=200000)
        assert U.reg_read(UC_ARM_REG_PC)==0x4000000
    ys=[]
    for i,item in enumerate(allgroups[2]):
        ptr=item['ptr']; original=item['rect']
        U.mem_write(ptr+10,struct.pack('<h',original[1]-64))
        call(0x598a4,[OBJ,0x200c000,i])
        rect=struct.unpack('<4h',U.mem_read(0x200c000,8))
        assert rect==(original[0]+8,original[1]-128,original[2],original[3]),rect
        assert rect[1]>=0 and rect[1]+rect[3]<=192
        ys.append(rect[1])
    print('PASS original ARM layout helper: final HUD Y=',ys,'; X +8; sizes unchanged')
    call(0xfcd4,[0x200b000])
    clip=struct.unpack('<4h',U.mem_read(0x200b144,8))
    assert clip==(0,0,256,192),clip
    print('PASS original ARM clip reset: 256x192 viewport')
