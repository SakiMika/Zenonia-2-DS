"""Use real native static-image centering/draw code and real installer policy.
Width/height/final draw are external stubs. No full ROM screenshot claim.
"""
from pathlib import Path
import struct,re,zlib
root=Path(__file__).resolve().parents[1]
s=(root/'tests/title_labels_arm_test.py').read_text()
exec(compile(s[:s.index('# Verify the actual resource')],str(root/'tests/title_labels_arm_test.py'),'exec'))
policy=(root/'source/zen_native_layout_policy.h').read_text()
shift=int(re.search(r'TitleCopyrightShiftY\s*=\s*(-?\d+)',policy)[1]);assert shift==-32
code=(root/'source/zen_native_layout.cpp').read_text()
assert '0x3c00u-ZenNativeLayout::TitleCopyrightShiftY' in code
assert 'TitleAnimationShiftY' in code[code.index('zen_title_animation_draw'):code.index('static bool ram(')]
# Native title image stream contains the147x11 copyright-sized bitmap.
b=(root/'zenonia2nds/menu/Title_1.pzx').read_bytes();images=zlib.decompress(b[1829:])
off=struct.unpack_from('<I',images,8)[0]
assert struct.unpack_from('<HH',images,off)==(147,11)
# Set up the native resource chain for direct static image path5a712.
ASPR,AVT,OWNER2,HOLDER2,TABLE2=range(0x200e000,0x200e500,0x100)
w(OWNER2+8,HOLDER2);w(HOLDER2+8,TABLE2);w(TABLE2,ASPR);w(ASPR,AVT)
w(AVT+0x1c,0x4000221);w(AVT+0x20,0x4000241);w(AVT+0x14,0x4000281)
w(0x1400070,0x2001000);w(0x2001008,0x2001100);w(0x2001100,0x2001200)
width,height=147,11
received=[]
def metrics(uc,a,n,d):
 if a==0x4000220:ret(width)
 elif a==0x4000240:ret(height)
 elif a==0x1400e4c:ret(192)
 elif a==0x4000280:
  received.append((rr(0),rr(1),rr(2),rr(3),bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP),8))));ret()
u.hook_add(UC_HOOK_CODE,metrics)
original=bytes.fromhex('3368041c1b6a301c');assert bytes(u.mem_read(0x5a744,8))==original
TRAMP=WRAP+0x200
u.mem_write(0x5a744,struct.pack('<2HI',0x4a00,0x4710,TRAMP|1))
for width,height in [(147,11),(112,60),(92,9)]:
 before=None
 for dy in [-64,shift]:
  u.mem_write(TRAMP,original+struct.pack('<4HI',0x3c00-dy,0x4a01,0x4710,0x46c0,0x5a74d))
  u.ctl_remove_cache(TRAMP,TRAMP+20);u.ctl_remove_cache(0x5a744,0x5a750)
  for _ in range(20):
   u.reg_write(UC_ARM_REG_R7,OWNER2);received.clear();calls.clear();run(0x5a712,0x5a76a)
   assert len(received)==1,received
   a,x,y,mode,args=received[0]
   assert a==ASPR and x==(256-width)//2 and y==192-height+dy and mode==0 and args==b'\0'*8
  if before is None:before=received[0]
  else:
   assert received[0][2]==before[2]+32
   assert received[0][:2]+received[0][3:]==before[:2]+before[3:]
# Real dimensions: old117..127 -> new149..159; blink anchor remains169.
assert 192-11+shift==149 and 192+shift==160
assert re.search(r'TitleLabelsShiftY\s*=\s*-96',policy)
assert 265-96==169 and 160<169
print('PASS real native static-image draw + copyright policy: 147x11 Y117->149, X54 unchanged; bottom160, above prompt169; repeated calls do not drift; mode/stack/sprite unchanged')
