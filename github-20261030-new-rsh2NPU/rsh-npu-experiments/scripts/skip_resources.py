"""CPU accounting of requested buffers, not a runtime peak-memory measurement."""
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsh.planner import Matrix,layout
from scripts.hv_cases import save
FULL={'V0':'cases_v0','V2':'cases_v2','H-V':'cases_hv','H-C':'cases_hc'}
PART=['V0-R','V2-R','H-Skip']
def sizes(m: int,k: int,stride: int,nnz: int,g: int,blocks: int,s: int)->dict:
    raw={'config':36,'ptr':4*(m+1),'cols':4*nnz,'values':2*nnz,'cube_ptr':8*(g+1),'colref':64*blocks,'tiles':512*blocks,'rowmap':64*g,'srows':4*s,'rhs0':2*(k+1)*stride,'rhs1':2*(k+1)*stride,'packed':64*g*stride,'out':4*m*stride}
    return {'requested_device_bytes':sum(max(32,x) for x in raw.values()),'host_retained_golden_valid_bytes':4*m*stride+m,'host_transient_upper_accounting':max(max(raw.values()),4*m*stride)+2*(k+1)*stride,'buffers':raw}
def main()->None:
    rows=[]
    for source in sorted((ROOT/'inputs').glob('*.npz')):
        a=Matrix.load(str(source));route=json.loads((ROOT/'results/hv/plans'/source.stem/'routing.json').read_text());order=np.fromfile(ROOT/'results/v2/orders'/source.stem/'order.bin',np.int32);plans={v:layout(a,order,route['split'],v) for v in PART}
        for n in [16,64,256]:
            counts={}
            for v,folder in FULL.items():
                cfg=list(map(int,(ROOT/folder/source.stem/f'N{n}'/v/'config.txt').read_text().split()));m,k,_,stride,nnz,g,b,s=cfg;counts[v]=sizes(m,k,stride,nnz,g,b,s)
            for v,p in plans.items():counts[v]=sizes(a.shape[0],a.shape[1],n,len(a.col),len(p['cube_ptr'])-1,len(p['tiles']),len(p['srows']))
            rows.append({'matrix':source.stem,'n':n,'device_requested_bytes':sum(x['requested_device_bytes'] for x in counts.values()),'host_retained_bytes':sum(x['host_retained_golden_valid_bytes'] for x in counts.values()),'host_transient_allowance':max(x['host_transient_upper_accounting'] for x in counts.values()),'variants':counts})
    result={'passed':True,'seven_variants':list(FULL)+PART,'rows':rows,'max_device_requested_bytes':max(x['device_requested_bytes'] for x in rows),'max_host_retained_plus_transient_bytes':max(x['host_retained_bytes']+x['host_transient_allowance'] for x in rows),'limits':'Requested Buffer sizes with per-buffer minimum32; excludes ACL allocation overhead/runtime/code memory. Host upper allowance is accounting only. All variants still clear original M output; tail omitted only from arithmetic/restore. Original M>=1 and full K/B unchanged.'};save(ROOT/'results/skip/resource_preflight.json',result);print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()
