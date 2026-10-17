"""Run original native7e450 PZX fragment parser on real GameUI metadata.
File-read/allocator services are emulated; record layout is NOT synthesized.
"""
from pathlib import Path
import zlib,struct
root=Path(__file__).resolve().parents[1]
s=(root/'tests/hud_pixel_arm_test.py').read_text()
exec(compile(s[:s.index('u.hook_add(')],str(root/'tests/hud_pixel_arm_test.py'),'exec'))
PARSER=0x020a0000;FILE=0x020a0100;OBJ=0x020a0200;REF=0x020a0300;FR=0x020a0400;IDX=0x020a1000;READ=0x04000100
blob=(root/'zenonia2nds/com/GameUI.pzx').read_bytes();meta=zlib.decompress(blob[70:]);pos=0;groups=[];raws=[]
for g in range(10):
 n=struct.unpack_from('<H',meta,pos)[0];pos+=2;start=pos;rows=[]
 for j in range(n):
  im,x,y,flags=struct.unpack_from('<HhhB',meta,pos);pos+=7
  if flags:pos+=1
  rows.append((im,x,y))
 raws.append(meta[start:pos]);groups.append(rows)
stream=b'';cursor=0;heap=0x020b0000
def read_hook(u,a,n,d):
 global cursor,heap
 if a==STOP:u.emu_stop()
 elif a==READ:
  dst=u.reg_read(regs[1]);size=u.reg_read(regs[2]);chunk=stream[cursor:cursor+size];assert len(chunk)==size
  u.mem_write(dst,chunk);cursor+=size;ret(size)
 elif a in [0x1400a0c,0xa33c]:
  p=heap;heap+=(u.reg_read(regs[0])+15)&~15;ret(p)
u.hook_add(UC_HOOK_CODE,read_hook)
u.mem_write(PARSER+0x11,b'\1');w(FILE,1);w(FILE+0x1c,READ|1);w(REF,OBJ);w(OBJ+8,FR)
for g in [1,2,3,9]:
 stream=raws[g];cursor=0;u.mem_write(FR,b'\0'*1024)
 sp=0x0300f000;u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,STOP)
 for reg,v in zip(regs,[PARSER,FILE,len(groups[g]),REF]):u.reg_write(reg,v)
 u.mem_write(sp,struct.pack('<2I',IDX,0))
 u.emu_start(0x7e451,STOP,count=300000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP and cursor==len(stream)
 parsed=[]
 for j in range(len(groups[g])):
  im=struct.unpack('<H',u.mem_read(IDX+j*2,2))[0];x,y=struct.unpack('<hh',u.mem_read(FR+j*24+4,4));parsed.append((im,x,y))
 assert parsed==groups[g],(g,parsed,groups[g])
print('PASS actual PZX7e450 parser: GameUI groups1/2/3/9, counts4/11/1/1, original fragment stride24 and y fields+6 verified')
