#!/usr/bin/env python3
"""Homebrew identity and capacity for a runner with NO embedded game files."""
from pathlib import Path
import struct,sys

def crc16_nds(data):
    crc=0xffff
    for b in data:
        crc^=b
        for _ in range(8):crc=(crc>>1)^(0xa001 if crc&1 else 0)
    return crc&0xffff

def patch(path):
    path=Path(path);d=bytearray(path.read_bytes())
    if len(d)<0x160:raise ValueError('NDS header too small')
    u32=lambda o:struct.unpack_from('<I',d,o)[0]
    if u32(0x20)!=0x8000 or u32(0x84)!=0x8000:raise ValueError('Use ndstool -h 0x8000 for the ARM9 homebrew layout')
    if u32(0x4c)!=0:raise ValueError('Embedded FAT file table detected: runner must not contain game files')
    # Pad only to the capacity actually needed by the executable/banner. No
    # fixed 8 MiB game-sized padding; a small rebuild remains a small runner.
    capacity=128*1024
    while capacity<len(d):capacity*=2
    if capacity>128*1024*1024:raise ValueError('Runner ROM unexpectedly large')
    d.extend(b'\xff'*(capacity-len(d)))
    d[:12]=b'ZENONIA2 DS ';d[12:16]=b'####'
    d[0x14]=(capacity//(128*1024)).bit_length()-1
    struct.pack_into('<H',d,0x15e,crc16_nds(d[:0x15e]))
    path.write_bytes(d)
    print('[HEADER] external folder /zenonia2nds/; #### DLDI; no embedded files; ROM',len(d),'bytes')
    return d

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: patch_nds_header.py runner.nds')
    try:patch(sys.argv[1])
    except (OSError,ValueError) as e:raise SystemExit(str(e))
