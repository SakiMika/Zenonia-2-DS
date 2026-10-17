from pathlib import Path
import struct,json
root=Path(__file__).resolve().parents[1]
rows=[]
for p in sorted((root/'zenonia2nds/map').glob('*.map')):
 v,kind,w,h=struct.unpack('<4I',p.read_bytes()[:16]);assert v==1 and kind==3 and 0<w<253 and 0<h<125
 rows.append(dict(file=p.name,width=w,height=h,area=w*h))
report=dict(count=len(rows),widest=max(rows,key=lambda r:r['width']),tallest=max(rows,key=lambda r:r['height']),largest_area=max(rows,key=lambda r:r['area']),maps=rows)
if __name__=='__main__':print(json.dumps(report,indent=2))
