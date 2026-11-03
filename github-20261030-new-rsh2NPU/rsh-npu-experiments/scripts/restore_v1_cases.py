"""Restore measured V1 binary layouts on CPU and verify their saved SHA256."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import tempfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsh.planner import Matrix,layout
from rsh.prepare import export


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest=json.loads((ROOT/'results/v1/manifest.json').read_text());records=[]
    for name,h in manifest['inputs'].items():
        source=ROOT/'inputs'/name;assert digest(source)==h
        a=Matrix.load(str(source));plan=layout(a,np.arange(a.shape[0]),{'w':16,'tail':[]},'V1')
        for n in [16,64,256]:
            base=ROOT/'cases_v0'/Path(name).stem/f'N{n}'/'V0'
            target=ROOT/'cases_v1'/Path(name).stem/f'N{n}'/'V1'
            metadata=json.loads((target/'metadata.json').read_text());expected=metadata['files_sha256']
            stride=(n+15)//16*16
            if not all((target/f'{key}.bin').exists() and digest(target/f'{key}.bin')==v for key,v in expected.items()):
                b=np.fromfile(base/'rhs.bin',np.float16).reshape(a.shape[1]+1,stride)[:a.shape[1],:n]
                golden=np.fromfile(base/'golden.bin',np.float32).reshape(a.shape[0],stride)[:,:n]
                with tempfile.TemporaryDirectory(prefix='restore-v1-',dir=ROOT) as td:
                    temp=Path(td);export(a,plan,b,golden,temp,metadata)
                    for key,v in expected.items():assert digest(temp/f'{key}.bin')==v,(name,n,key)
                    for f in temp.iterdir():
                        if f.name!='metadata.json':shutil.move(str(f),target/f.name)
            link=target.parent/'V0'
            if not link.exists():link.symlink_to(os.path.relpath(base,link.parent),target_is_directory=True)
            records.append({'matrix':name,'n':n,'binary_files_verified':len(expected)})
            print('V1_RECOVERED_EXACT',name,n,flush=True)
    assert len(records)==24
    (ROOT/'results/v1/local_data_recovery.json').write_text(json.dumps({'passed':True,'configurations':24,'records':records},indent=2))
    print('ALL_V1_BINARY_DATA_RECOVERED',24,flush=True)


if __name__=='__main__':main()
