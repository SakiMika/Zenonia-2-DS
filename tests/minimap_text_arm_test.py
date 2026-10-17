"""v046 regression: actual general text engine AND actual FT2 rasterizer.
Only strlen/context/WIPI framebuffer hardware services are stubbed. Numeric
1683c regression demonstrates why the v045 clock font is unsafe for names.
"""
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
root=Path(__file__).resolve().parents[1]
u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
with (root/'zenonia2nds/binary.mod').open('rb') as f:
 e=ELFFile(f)
 for sn in ['.text','.data','.bss']:
  s=e.get_section_by_name(sn);a=s['sh_addr'];n=s['sh_size'];u.mem_map(a&~4095,((n+(a&4095)+4095)//4096)*4096)
  if sn!='.bss':u.mem_write(a,s.data())
u.mem_map(0x02000000,0x80000)
WRAP,FONT,DATA,CTX,FB,NAME,PIX,STOP,STACK,ATLAS=0x02001000,0x02002000,0x02003000,0x02004000,0x02004100,0x02005000,0x02010000,0x02008000,0x02070000,0x02009000
font_data=(root/'zenonia2nds/font/synGulimAsc5_11.ft2').read_bytes();assert len(font_data)==660 and font_data[:2]==bytes([5,11])
def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
R=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def rr(i):return u.reg_read(R[i])
u.mem_write(DATA,font_data+bytes(4));w(WRAP+12,1);w(WRAP+16,FONT)
w(FONT+4,DATA);w(FONT+12,CTX);w(FONT+0x40,256);w(FONT+0x44,192)
u.mem_write(FONT+0x38,struct.pack('<4h',0,0,256,192))
u.mem_write(FONT+0x56,bytes([5,11]));u.mem_write(FONT+0x5a,bytes([1,1,11,0,7]));w(CTX,FB)
w(ATLAS+8,ATLAS+0x100)
glyphs=[];stops=0
imports={0x140096c,0x1400e5c,0x1400e2c,0x1400e3c}
def hook(u,a,n,d):
 global stops
 if a==STOP:stops+=1;u.emu_stop()
 elif a==0x1220:ret(CTX)
 elif a==0x140096c:
  p=rr(0);b=bytes(u.mem_read(p,128));ret(b.index(0))
 elif a==0x1400e5c:ret(16)
 elif a==0x1400e2c:ret(PIX)
 elif a==0x1400e3c:ret(256)
 elif a==0xdae8:
  sp=u.reg_read(UC_ARM_REG_SP);h=word(sp);p=word(sp+4)
  assert h==11 and DATA+2<=p and p+7<=DATA+len(font_data),(hex(p),h)
  glyphs.append(p)
u.hook_add(UC_HOOK_CODE,hook)
def run(fn,args,stackargs=()):
 before=stops;u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP|1)
 for r,v in zip(R,args):u.reg_write(r,v&0xffffffff)
 for i,v in enumerate(stackargs):w(STACK+4*i,v)
 u.emu_start(fn|1,0,count=1000000)
 assert stops==before+1 and u.reg_read(UC_ARM_REG_SP)==STACK,'native call did not return cleanly'
 return rr(0)
# The old formatter uses raw character-48 as an unchecked sprite index.
run(0x1683c,[ATLAS,ord('y')-48]);bad=rr(0)
assert bad>=ATLAS+0x100+18*24
print('REPRO v045: numeric glyph accessor maps y to sprite73, outside the18-sprite test fixture (not a full-game crash reproduction)')
# Real general-font renderer and bit rasterizer, not text/graphics stubs.
for offset in [0,64,-64,128]:
 w(CTX+0x40,offset);w(FONT+0x44,192-offset)
 for text in [b'Ayles Town',b'Forest of Trials',b'0 1 3 7 9 * #']+[bytes([c]) for c in range(33,127)]:
  u.mem_write(NAME,text+b'\0'+bytes(128-len(text)-1));u.mem_write(PIX,bytes(256*192*2));glyphs.clear()
  # Red-zone sentinels around the capture; text belongs in Y128..138.
  u.mem_write(PIX-16,b'G'*16);u.mem_write(PIX+256*192*2,b'H'*16)
  run(0x5f108,[WRAP,NAME,0,128-offset],[0xffff,-1,-1])
  assert glyphs and any(u.mem_read(PIX+128*512,11*512)),(offset,text,glyphs[:2])
  assert not any(u.mem_read(PIX,128*512)) and not any(u.mem_read(PIX+139*512,53*512)),(offset,text,glyphs[:2])
  assert bytes(u.mem_read(PIX-16,16))==b'G'*16 and bytes(u.mem_read(PIX+256*192*2,16))==b'H'*16
  assert word(FONT+0x48)==0xffff
print('PASS native5f108 -> e0f4 -> dae8: names, digits/symbols, all94 printable glyphs; actual FT2 pixels in Y128..138; no capture overrun; viewport offsets0/+64/-64/+128')
# Source guard: installer must never select numeric5f578 for a map name again.
s=(root/'source/zen_native_minimap.cpp').read_text()
assert 'lgt_translate_ptr(img,0x5f108)' in s and 'lgt_translate_ptr(img,0x5f578)' not in s
assert '128-offset' in s and 'ram(font,0x6c)' in s and 'saved_font[0x68/4]=0' in s
print('PASS map-title source uses general string renderer and a complete0x6c font snapshot, callbacks disabled')
