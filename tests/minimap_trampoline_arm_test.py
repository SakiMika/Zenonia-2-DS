"""Execute the original native minimap prologue and exact v045 trampoline.
Also execute native early-return path with context service stubbed.
"""
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
root=Path(__file__).resolve().parents[1]
with (root/'zenonia2nds/binary.mod').open('rb') as f:
 e=ELFFile(f);text=e.get_section_by_name('.text');address=text['sh_addr'];data=text.data()
assert data[0x2f400-address:0x2f408-address]==bytes.fromhex('f0b5ca4b8db0071c')
TRAMP=0x02010000;CTX=0x02001000;STATE=0x02002000;SELF=0x02003000;SP=0x02018000;STOP=0x02000100
regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_SP,UC_ARM_REG_LR]
def run(start,early=False):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0x90000);u.mem_write(address,data);u.mem_map(0x02000000,0x20000)
 u.mem_write(TRAMP,struct.pack('<8H2I',0xb5f0,0x4b03,0xb08d,0x1c07,0x4c02,0x4720,0x46c0,0x46c0,0x1215,0x2f409))
 u.mem_write(CTX+0xa8,struct.pack('<I',STATE));u.mem_write(STATE+0x30,bytes(4))
 for i,r in enumerate(regs):u.reg_write(r,0x100+i)
 u.reg_write(UC_ARM_REG_R0,SELF);u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP|1)
 def hook(u,a,n,d):
  if a==(STOP if early else 0x2f408):u.emu_stop()
  elif a==0x1214:u.reg_write(UC_ARM_REG_R0,CTX);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(start|1,0,count=300)
 return [u.reg_read(r) for r in regs],bytes(u.mem_read(SP-0x48,0x48))
a,stack=run(0x2f400);b,stack2=run(TRAMP)
# r4 is the documented dead scratch until native 2f454 overwrites it.
assert all(a[i]==b[i] for i in range(len(a)) if i!=4) and stack==stack2
assert b[4]==0x2f409 and b[7]==SELF and b[3]==0x1215 and b[8]==SP-0x48
for start in [0x2f400,TRAMP]:
 r,_=run(start,True);assert r[8]==SP and r[4:8]==[0x104,0x105,0x106,0x107]
print('PASS real Thumb minimap prologue/trampoline: relocated context, self/SP/saved registers; native early-return unwinds stack')
