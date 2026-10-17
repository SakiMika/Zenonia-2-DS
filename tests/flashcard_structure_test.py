"""Source/header checks. Does not claim an actual ARM9 build or DLDI test."""
from pathlib import Path
import importlib.util,struct,tempfile
r=Path(__file__).resolve().parents[1]
main=(r/'source/main.cpp').read_text();mk=(r/'Makefile').read_text()
assert 'nitroFSInit' not in main and '<filesystem.h>' not in main
assert main.index('wipi_init_storage();')<main.index('embedded_assets_init()')<main.index('embedded_asset_find("binary.mod"')
assert 'NITRO       := nitrofs' not in mk and 'NITRO_FILES)' not in mk
assert '$(_ADDFILES)' not in mk and 'payload-check' not in mk and '-lfilesystem' not in mk
assert 'LIBS        := -lfat -lnds9' in mk and '-g "####"' in mk
assert 'RUNNER_ASSET_COUNT' not in (r/'source/runner_package_config.h').read_text()
for p in (r/'source').glob('*.cpp'):assert 'nitro:/' not in p.read_text(),p.name
spec=importlib.util.spec_from_file_location('header',r/'tools/patch_nds_header.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'runner.nds';b=bytearray(600000);struct.pack_into('<I',b,0x20,0x8000);struct.pack_into('<I',b,0x84,0x8000);p.write_bytes(b)
 result=m.patch(p);assert len(result)==1024*1024 and result[12:16]==b'####' and result[0x14]==3
 assert struct.unpack_from('<H',result,0x15e)[0]==m.crc16_nds(result[:0x15e])
 assert struct.unpack_from('<I',result,0x4c)[0]==0
 assert result[:12]==b'ZENONIA2 DS '
 assert 'GAME_TITLE      := Zenonia 2 DS Runner' in mk
 assert '@mv -f "$(TARGET).nds" "Zenonia 2 DS Runner.nds"' in mk
 b[0x4c:0x50]=struct.pack('<I',8);p.write_bytes(b)
 try:m.patch(p)
 except ValueError:pass
 else:raise AssertionError('Embedded payload accepted')
 b[0x4c:0x50]=bytes(4);b[0x20:0x24]=struct.pack('<I',0x4000);p.write_bytes(b)
 try:m.patch(p)
 except ValueError:pass
 else:raise AssertionError('Wrong ARM9 layout accepted')
print('PASS source has no embedded-game build dependency; metadata independent; runner header capacity/CRC; rejects embedded FAT and wrong ARM9 layout')
