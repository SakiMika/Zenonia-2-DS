from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
if not (root/'zenonia2nds/binary.mod').is_file():raise SystemExit('Fixture required: prepare zenonia2nds/ first; run tests/run_flashcard_tests.sh for data-free tests.')
s=(root/'source/wipi_shim.cpp').read_text()
def func(marker):
 a=s.index(marker);b=s.index('{',a);n=1;p=b+1
 while n:
  if s[p]=='{':n+=1
  elif s[p]=='}':n-=1
  p+=1
 return s[a:p]
a=s.index('struct BootCostScope {');b=s.index('extern "C" int knl_get_resource_id(',a)
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'audio_decode_entry.inc').write_text(s[a:b]+func('static int media_decode(DummyMediaClip *c)'))
 subprocess.run(['g++','-O2','-std=c++17','-Wall','-Wextra','-I'+str(d),str(root/'tests/predecoded_audio_test.cpp'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test'),str(d/'cache.zpc')],cwd=root,check=True)
subprocess.run(['python','tools/render_title_pcm.py','--verify'],cwd=root,check=True)
