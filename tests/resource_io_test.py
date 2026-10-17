"""Compile actual WIPI entry points with low-address host handles and asset IO.
No emulator timing claim: counts payload reads and checks bytes/errors only.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
if not (root/'zenonia2nds/binary.mod').is_file():raise SystemExit('Fixture required: prepare zenonia2nds/ first; run tests/run_flashcard_tests.sh for data-free tests.')
s=(root/'source/wipi_shim.cpp').read_text()
a=s.index('struct BootCostScope {')
b=s.index('extern "C" int knl_printk(',a)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)
 (p/'resource_entry_points.inc').write_text(s[a:b])
 subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-fno-pie','-no-pie','-I'+d,str(root/'tests/resource_io_test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],cwd=root,check=True)
