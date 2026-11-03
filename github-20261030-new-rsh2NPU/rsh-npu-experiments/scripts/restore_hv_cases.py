"""Restore H-V binary cases on CPU from frozen routing; no device work."""
from pathlib import Path
import json,os,shutil,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsh.planner import Matrix,layout
from rsh.prepare import export
from scripts.hv_cases import digest,check_split,save

def main()->None:
    dest=ROOT/'results/hv';manifest=json.loads((dest/'manifest.json').read_text());records=[]
    for name,h in manifest['inputs'].items():
        src=ROOT/'inputs'/name;assert digest(src)==h;a=Matrix.load(str(src));pd=dest/'plans'/src.stem
        routing=json.loads((pd/'routing.json').read_text());stats=json.loads((pd/'structure.json').read_text());assert digest(pd/'routing.json')==stats['routing_sha256']
        od=ROOT/'results/v2/orders'/src.stem/'order.bin';assert digest(od)==routing['order_sha256']==manifest['orders'][src.stem]
        order=np.fromfile(od,np.int32);split=routing['split'];check_split(a,split);plan=layout(a,order,split,'H-V')
        for n in [16,64,256]:
            base=ROOT/'cases_v0'/src.stem/f'N{n}/V0';target=ROOT/'cases_hv'/src.stem/f'N{n}/H-V';meta=json.loads((target/'metadata.json').read_text());expected=meta['files_sha256'];stride=(n+15)//16*16
            if not all((target/f'{key}.bin').exists() and digest(target/f'{key}.bin')==v for key,v in expected.items()):
                b=np.fromfile(base/'rhs.bin',np.float16).reshape(a.shape[1]+1,stride)[:a.shape[1],:n];gold=np.fromfile(base/'golden.bin',np.float32).reshape(a.shape[0],stride)[:,:n]
                with tempfile.TemporaryDirectory(prefix='restore-hv-',dir=ROOT) as td:
                    temp=Path(td);export(a,plan,b,gold,temp,meta)
                    for key,v in expected.items():assert digest(temp/f'{key}.bin')==v,(name,n,key)
                    for f in temp.iterdir():
                        if f.name!='metadata.json':shutil.move(str(f),target/f.name)
            for v in ['V0','V2']:
                control=ROOT/f'cases_{v.lower()}'/src.stem/f'N{n}'/v;link=target.parent/v
                if not link.exists():link.symlink_to(os.path.relpath(control,link.parent),target_is_directory=True)
            records.append({'matrix':src.stem,'n':n,'verified_files':len(expected)});print('HV_RECOVERED_EXACT',src.stem,n,flush=True)
    assert len(records)==24;save(dest/'local_data_recovery.json',{'passed':True,'configurations':24,'records':records})
if __name__=='__main__':main()
