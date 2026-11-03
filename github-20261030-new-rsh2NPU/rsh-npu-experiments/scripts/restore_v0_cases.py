"""Recover V0 binary inputs locally, verifying against the measured metadata.

CPU/file operations only. Never starts an NPU experiment or edits measured data.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile

import numpy as np
from scipy.sparse import csr_matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsh.planner import Matrix,layout
from rsh.prepare import export


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest=json.loads((ROOT/'results/v0/manifest.json').read_text())
    records=[]
    for name,expected_input in manifest['inputs'].items():
        source=ROOT/'inputs'/name
        assert sha(source)==expected_input,source
        a=Matrix.load(str(source))
        plan=layout(a,np.arange(a.shape[0]),{'w':16,'tail':[]},'V0')
        ref=csr_matrix((a.val.astype(np.float64),a.col,a.ptr),shape=a.shape)
        for n in [16,64,256]:
            target=ROOT/'cases_v0'/Path(name).stem/f'N{n}'/'V0'
            metadata=json.loads((target/'metadata.json').read_text())
            expected=metadata['files_sha256']
            if not all((target/f'{key}.bin').exists() and sha(target/f'{key}.bin')==h for key,h in expected.items()):
                b=np.random.default_rng(20261017+n).uniform(-1,1,(a.shape[1],n)).astype(np.float16)
                golden=(ref@b.astype(np.float64)).astype(np.float32)
                with tempfile.TemporaryDirectory(prefix='restore-v0-',dir=ROOT) as td:
                    temp=Path(td)
                    export(a,plan,b,golden,temp,metadata)
                    for key,h in expected.items():
                        assert sha(temp/f'{key}.bin')==h,f'Recovered data differ: {name}/N{n}/{key}'
                    for f in temp.iterdir():
                        if f.name!='metadata.json':shutil.move(str(f),target/f.name)
            assert (target/'config.txt').exists()
            records.append({'matrix':name,'n':n,'binary_files_verified':len(expected)})
            print('RECOVERED_EXACT',name,n,flush=True)
    out=ROOT/'results/v0/local_data_recovery.json'
    out.write_text(json.dumps({'passed':True,'configurations':len(records),'records':records,
                              'method':'Reconstructed CPU data match every remote measured binary SHA256.'},indent=2))
    print('ALL_V0_DATA_RECOVERED_AND_VERIFIED',len(records),flush=True)


if __name__=='__main__':main()
