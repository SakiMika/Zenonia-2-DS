"""Optional UI art regeneration; requires Pillow. No game assets modified."""
from PIL import Image,ImageOps
from pathlib import Path
import colorsys
root=Path(__file__).resolve().parents[1]
src=Image.open(root/'assets/ui/reference-melee.jpg').convert('RGB')
bar=src.crop((44,17,189,43))
# Preserve the actual MELEE ornamental end caps; remove text from the center.
for y in range(bar.height):
 for x in range(bar.width):
  r,g,b=bar.getpixel((x,y)); h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
  if s>.2:r,g,b=[int(t*255) for t in colorsys.hsv_to_rgb(.755,s*.7,v)]
  if 30<=x<112 and 5<=y<21:
   r,g,b=(37,21,59) if y not in (5,20) else (99,67,132)
  if max(r,g,b)<28:r,g,b=(20,11,32)
  bar.putpixel((x,y),(r,g,b))
# Nine-slice horizontal stretch with untouched ornamental ends, then DS sizing.
wide=Image.new('RGB',(234,26));wide.paste(bar.crop((0,0,31,26)),(0,0));wide.paste(bar.crop((112,0,145,26)),(201,0));wide.paste(bar.crop((31,0,112,26)).resize((170,26)),(31,0));bar=wide.resize((234,22),Image.Resampling.LANCZOS)
bar.save(root/'assets/ui/place_bar.png')
logo=Image.open(root/'assets/ui/reference-logo.webp').convert('RGB').resize((35,29),Image.Resampling.LANCZOS)
for y in range(29):
 for x in range(35):
  r,g,b=logo.getpixel((x,y));h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255);logo.putpixel((x,y),tuple(int(t*255) for t in colorsys.hsv_to_rgb(.76,s*.7,v*.8)))
logo.save(root/'assets/ui/logo.png')
with (root/'source/zen_map_art.h').open('w') as f:
 f.write('// Derived from user-supplied MELEE frame and Zenonia 2 logo. DS RGB555.\n#pragma once\n#include <stdint.h>\n')
 for name,im in [('place_bar',bar),('map_logo',logo)]:
  vals=[0x8000|(r>>3)|((g>>3)<<5)|((b>>3)<<10) for r,g,b in im.getdata()]
  f.write('static const uint16_t '+name+'[] = {\n')
  for n in range(0,len(vals),24):f.write(','.join(hex(v) for v in vals[n:n+24])+',\n')
  f.write('};\n')
