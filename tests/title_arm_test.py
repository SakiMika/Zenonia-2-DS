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
calls=[];stops=set()
def hook(uc,a,n,d):
 if a in stops:uc.emu_stop();return
 if a==0x1400e3c:ret(256)
 elif a==0x1400e4c:ret(192)
 elif a==0x1400ccc:ret(0xffff)
 elif a in [0x1046c,0x15564,0x15588]:ret()
 elif a==0x81354:
  u.mem_write(rr(0),bytes([rr(1)&255])*rr(2));ret(rr(0))
 elif a==0x14009dc:
  assert text(rr(1))==b'%s%s'
  u.mem_write(rr(0),text(rr(2))+text(rr(3))+b'\0');ret()
 elif a==0x1214:ret(0x2005000)
 elif a==0x157e0:
  calls.append(('text',rr(2),rr(3),text(rr(1))));ret()
 elif a==0x4000120:ret(60) # synthetic static title logo height
 elif a==0x4000100:
  calls.append(('sprite',rr(1),rr(2),rr(3)));ret()
u.hook_add(UC_HOOK_CODE,hook)
def run(a,stop=0x4000000):
 stops.clear();stops.add(stop)
 u.reg_write(UC_ARM_REG_SP,0x30ff000);u.reg_write(UC_ARM_REG_LR,0x4000000)
 u.emu_start(a|1,stop,count=100000)
 assert u.reg_read(UC_ARM_REG_PC)==stop,hex(u.reg_read(UC_ARM_REG_PC))
# Actual complete warning draw function, external font/import calls stubbed.
w(0x1400070,0x2001000);w(0x2001008,0x2001100);w(0x2001100,0)
w(0x200509c,4) # blink-visible phase
run(0x5a9dc)
assert [c[2] for c in calls]==[16,186],calls
assert b'\xbe\xc6\xb9\xab' in calls[1][3] # Korean 'any key' message
calls.clear()
assert bytes(u.mem_read(0x5aab0,2))==bytes.fromhex('aa33')
assert bytes(u.mem_read(0x5aa3e,2))==bytes.fromhex('4010')
u.mem_write(0x5aa3e,bytes.fromhex('0420'))
u.ctl_remove_cache(0x5aa3e,0x5aa40)
u.mem_write(0x5aab0,bytes.fromhex('a233'))
u.ctl_remove_cache(0x5aab0,0x5aab2)
run(0x5a9dc)
assert [c[2] for c in calls]==[4,166],calls
print('PASS native warning function: body y16 ->4; blinking prompt y186 ->166 (v035 y166 retained)')
# A Thumb tail wrapper equivalent to the tested C++ wrapper. Saves original
# r3 (mode), changes only y, restores stack args, then enters REAL native draw.
WRAP=0x2006000
u.mem_write(WRAP,bytes.fromhex('08b4024b9c4608bc403a6047')+struct.pack('<I',0x70e85))
for pool in [0x5a908,0x5b3ec]:
 assert struct.unpack('<I',u.mem_read(pool,4))[0]==0x70e85
 w(pool,WRAP|1)
ANIM,STATE,FRAME,SPRITE,VT=0x2007000,0x2007100,0x2007200,0x2007300,0x2007400
w(ANIM+8,STATE);w(ANIM+16,FRAME);w(FRAME,SPRITE);w(SPRITE,VT);w(VT+16,0x4000101)
# Execute all four original title call sequences and the original animation
# draw + coordinate helper (0x70e84/0x70db8), stubbing only final sprite draw.
for entry,stop in [(0x5a680,0x5a692),(0x5a6c0,0x5a6d2),(0x5b37c,0x5b38e),(0x5b3b0,0x5b3c2)]:
 for y in [0,192,264,265,319]:
  calls.clear();u.mem_write(FRAME+4,struct.pack('<hh',64,y));u.reg_write(UC_ARM_REG_R5,ANIM)
  run(entry,stop)
  assert calls==[('sprite',64,(y-64)&0xffffffff,0)],(hex(entry),y,calls)
print('PASS four native title call sites + original animation renderer: dy -64 only; x/mode unchanged')
print('LIMIT: synthetic sprite records, stub font/graphics calls; no full ROM or visual test')

# Exercise displaced logo instructions and native bottom-anchor calculation.
LOGO_TRAMP=0x2006100
expected=bytes.fromhex('3368041c1b6a301c')
assert bytes(u.mem_read(0x5a744,8))==expected
u.mem_write(LOGO_TRAMP,expected+struct.pack('<4H',0x3c40,0x4a01,0x4710,0x46c0)+struct.pack('<I',0x5a74d))
u.mem_write(0x5a744,struct.pack('<2HI',0x4a00,0x4710,LOGO_TRAMP|1))
u.ctl_remove_cache(0x5a744,0x5a74c)
w(VT+32,0x4000121);w(VT+20,0x4000101)
u.reg_write(UC_ARM_REG_R6,SPRITE);u.reg_write(UC_ARM_REG_R5,48);u.reg_write(R[0],192)
calls.clear();run(0x5a744,0x5a76a)
assert calls==[('sprite',48,192-60-64,0)],calls
print('PASS native static-logo trampoline: bottom anchor y132 ->68, same sprite/size/mode')
