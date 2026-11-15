"""Add per-tile permutation-A readback cases without changing any timing case."""
from pathlib import Path
import struct,shutil,json,hashlib
ROOT=Path(__file__).resolve().parent

def read(path:Path)->list[int]:
 raw=path.read_bytes();return list(struct.unpack('<'+'I'*(len(raw)//4),raw))

def write(path:Path,x:list[int])->None:path.write_bytes(struct.pack('<'+'I'*len(x),*x))

def main()->None:
 names=[]
 for source in (ROOT/'gate.list').read_text().splitlines():
  name='full-address-'+source;cfg=read(ROOT/'inputs'/(source+'.config.bin'));rows=read(ROOT/'inputs'/(source+'.rows.bin'));tiles=cfg[2];cfg[9]=tiles
  for ti in range(tiles):cfg[24+ti*3:24+ti*3+3]=[ti,0,1]
  lengths=[sum(r<0xffffff00 for r in rows[ti*16:ti*16+16]) for ti in range(tiles)];assert all(lengths)
  write(ROOT/'inputs'/(name+'.config.bin'),cfg);write(ROOT/'inputs'/(name+'.lengths.bin'),lengths)
  for suffix in ['rows','commands','offsets']:shutil.copyfile(ROOT/'inputs'/(source+'.'+suffix+'.bin'),ROOT/'inputs'/(name+'.'+suffix+'.bin'))
  names.append(name)
 (ROOT/'strong-gate.list').write_text('\n'.join(names)+'\n');print('STRONG_ADDRESS_INPUTS_READY',len(names),flush=True)
if __name__=='__main__':main()
