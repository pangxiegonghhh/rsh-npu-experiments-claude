"""Restore measured conditional-grid binaries from frozen routing on CPU."""
from pathlib import Path
import json,os,shutil,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.hv_cases import digest,check_split,save
from rsh.planner import Matrix,layout
from rsh.prepare import export

def main()->None:
    dest=ROOT/'results/hv/grid';records=[]
    for marker in sorted((ROOT/'cases_hv_grid').glob('t*/*/N*/H-V/metadata.json')):
        td,name,ns,_=marker.parent.relative_to(ROOT/'cases_hv_grid').parts;n=int(ns[1:]);target=marker.parent;meta=json.loads(marker.read_text());expected=meta['files_sha256'];src=ROOT/'inputs'/f'{name}.npz';a=Matrix.load(str(src))
        pd=dest/'plans'/td/name;route=json.loads((pd/'routing.json').read_text());assert digest(pd/'routing.json')==meta['routing_sha256'];od=ROOT/'results/v2/orders'/name/'order.bin';assert digest(od)==route['order_sha256'];order=np.fromfile(od,np.int32);check_split(a,route['split'])
        if not all((target/f'{key}.bin').exists() and digest(target/f'{key}.bin')==h for key,h in expected.items()):
            plan=layout(a,order,route['split'],'H-V');base=ROOT/'cases_v0'/name/f'N{n}/V0';stride=(n+15)//16*16;b=np.fromfile(base/'rhs.bin',np.float16).reshape(a.shape[1]+1,stride)[:a.shape[1],:n];gold=np.fromfile(base/'golden.bin',np.float32).reshape(a.shape[0],stride)[:,:n]
            with tempfile.TemporaryDirectory(prefix='restore-hv-grid-',dir=ROOT) as dd:
                temp=Path(dd);export(a,plan,b,gold,temp,meta)
                for key,h in expected.items():assert digest(temp/f'{key}.bin')==h,(td,name,key)
                for f in temp.iterdir():
                    if f.name!='metadata.json':shutil.move(str(f),target/f.name)
        for v,control in [('V0',ROOT/'cases_v0'/name/f'N{n}/V0'),('V2',ROOT/'cases_v2'/name/f'N{n}/V2'),('H-V-base',ROOT/'cases_hv'/name/f'N{n}/H-V')]:
            link=target.parent/v
            if not link.exists():link.symlink_to(os.path.relpath(control,link.parent),target_is_directory=True)
        records.append({'tau':td,'matrix':name,'n':n,'verified_files':len(expected)});print('HV_GRID_RECOVERED',td,name,n,flush=True)
    assert len(records)==24;save(dest/'local_data_recovery.json',{'passed':True,'configurations':24,'records':records})
if __name__=='__main__':main()
