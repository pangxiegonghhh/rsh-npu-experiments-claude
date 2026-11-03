"""Rebuild V2 on CPU using measured saved permutations, verify exact binaries."""
from pathlib import Path
import hashlib,json,os,shutil,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsh.planner import Matrix,layout
from rsh.prepare import export
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    manifest=json.loads((ROOT/'results/v2/manifest.json').read_text());records=[]
    for name,h in manifest['inputs'].items():
        source=ROOT/'inputs'/name;assert digest(source)==h;a=Matrix.load(str(source));od=ROOT/'results/v2/orders'/Path(name).stem
        stats=json.loads((od/'structure.json').read_text());assert digest(od/'order.bin')==stats['order_sha256']
        order=np.fromfile(od/'order.bin',np.int32);assert np.array_equal(np.sort(order),np.arange(a.shape[0]))
        plan=layout(a,order,{'w':16,'tail':[]},'V2')
        for n in [16,64,256]:
            base=ROOT/'cases_v0'/Path(name).stem/f'N{n}'/'V0';target=ROOT/'cases_v2'/Path(name).stem/f'N{n}'/'V2'
            metadata=json.loads((target/'metadata.json').read_text());expected=metadata['files_sha256'];stride=(n+15)//16*16
            if not all((target/f'{key}.bin').exists() and digest(target/f'{key}.bin')==v for key,v in expected.items()):
                b=np.fromfile(base/'rhs.bin',np.float16).reshape(a.shape[1]+1,stride)[:a.shape[1],:n]
                golden=np.fromfile(base/'golden.bin',np.float32).reshape(a.shape[0],stride)[:,:n]
                with tempfile.TemporaryDirectory(prefix='restore-v2-',dir=ROOT) as td:
                    temp=Path(td);export(a,plan,b,golden,temp,metadata)
                    for key,v in expected.items():assert digest(temp/f'{key}.bin')==v,(name,n,key)
                    for f in temp.iterdir():
                        if f.name!='metadata.json':shutil.move(str(f),target/f.name)
            for v in ['V0','V1']:
                control=ROOT/f'cases_{v.lower()}'/Path(name).stem/f'N{n}'/v;link=target.parent/v
                if not link.exists():link.symlink_to(os.path.relpath(control,link.parent),target_is_directory=True)
            records.append({'matrix':name,'n':n,'binary_files_verified':len(expected)});print('V2_RECOVERED_EXACT',name,n,flush=True)
    assert len(records)==24
    (ROOT/'results/v2/local_data_recovery.json').write_text(json.dumps({'passed':True,'configurations':24,'records':records},indent=2));print('ALL_V2_BINARY_DATA_RECOVERED',24,flush=True)
if __name__=='__main__':main()
