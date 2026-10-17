"""Execute original Thumb c844 and original RGB565 RLE writer758e4.
Only WIPI framebuffer accessors/context are stubs. Reproduce v040 overflow,
then assert v041 writes exactly a 240x60 panel at y132..191 and nowhere else.
Not a complete ROM, PZX loader or hardware/emulator visual test.
"""
import os,sys,struct
from pathlib import Path
if os.getenv('ZEN_RE_TOOLS'):sys.path.insert(0,os.environ['ZEN_RE_TOOLS'])
from unicorn import *
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
root=Path(__file__).resolve().parents[1]
u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
with (root/'zenonia2nds/binary.mod').open('rb') as f:
 e=ELFFile(f)
 for name in ['.text','.data','.bss']:
  s=e.get_section_by_name(name);a=s['sh_addr'];n=s['sh_size']
  u.mem_map(a&~4095,((n+(a&4095)+4095)//4096)*4096)
  if name!='.bss':u.mem_write(a,s.data())
u.mem_map(0x02000000,0x100000);u.mem_map(0x03000000,0x10000);u.mem_map(0x04000000,0x1000)
CTX=0x02001000;DST=0x02020000;SRC=0x02080000;PAL=0x02090000;STOP=0x04000000
regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def w(a,v):u.mem_write(a,struct.pack('<I',v))
def ret(v):u.reg_write(regs[0],v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
def hook(u,a,n,d):
 if a==STOP:u.emu_stop()
 elif a==0x1220:ret(CTX)
 elif a==0x1400e2c:ret(DST)
 elif a==0x1400e3c:ret(256)
 elif a==0x1400e4c:ret(192)
 elif a==0x1400e5c:ret(16)
u.hook_add(UC_HOOK_CODE,hook)
w(CTX,0x02001800);u.mem_write(CTX+0x44,struct.pack('<4h',0,0,256,192))
w(0x157d0f8,0x758e5);u.mem_write(PAL,struct.pack('<2H',0,0xf800))
# Encoded RLE: draw240 indices, then advance remaining16 columns for each row.
stream=b''.join(struct.pack('<H',0x8000|240)+b'\1'*240+struct.pack('<H',16) for _ in range(60))+struct.pack('<H',0xffff)
u.mem_write(SRC,stream)
def run(offset,y):
 w(CTX+0x40,offset);u.mem_write(DST,b'\0'*(256*400*2))
 sp=0x0300f000;u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,STOP)
 for reg,val in zip(regs,[0,y,240,60]):u.reg_write(reg,val)
 # stack args: encodedstream, sourcepalette, mode, scale, optionalfb
 u.mem_write(sp,struct.pack('<5I',SRC,PAL,0,0,0))
 u.emu_start(0xc845,STOP,count=1000000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP,hex(u.reg_read(UC_ARM_REG_PC))
 pixels=struct.unpack('<'+str(256*400)+'H',u.mem_read(DST,256*400*2))
 ys={i//256 for i,v in enumerate(pixels) if v}
 return pixels,ys
p,ys=run(128,132)
assert ys==set(range(260,320)),(min(ys),max(ys))
print('PASS reproduces v040: native raster re-adds128 and writes rows260..319 outside192-row HUD')
p,ys=run(0,132)
assert ys==set(range(132,192)),(min(ys),max(ys))
assert sum(v!=0 for v in p)==240*60
for y in range(400):
 for x in range(256):assert p[y*256+x]==(0xf800 if 132<=y<192 and x<240 else 0),(x,y)
print('PASS v041 native c844 + original RLE758e4: 14400 RGB565 pixels at240x60,y132..191; surrounding rows/columns untouched')
