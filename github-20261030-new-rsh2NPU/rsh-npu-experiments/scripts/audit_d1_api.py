"""Independent verification of supplementary API diagnostic; offline only."""
from pathlib import Path
import math,statistics,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import POINTS,ARGS,LABELS,sha,read,save
from scripts.run_d1 import validate
D=ROOT/'results/d1'
def main():
    assert read(D/'api_progress.json')['state']=='complete' and len(set(read(D/'api_progress.json')['completed']))==15
    b=read(D/'api_build.json');assert b['kernel_recompiled'] is False;assert sha(D/'device_binary/rsh_runner_api')==b['executable_sha256']
    for name,h in [('diagnostics/d1/api_runner.cpp',b['source_sha256']),('diagnostics/d1/profile_runner.cpp',b['parent_source_sha256'])]:assert sha(ROOT/name)==h
    for p in (D/'api_source_snapshot').rglob('*'):
        if p.is_file():assert sha(ROOT/p.relative_to(D/'api_source_snapshot'))==sha(p)
    x=read(D/'api_analysis.json');assert x['passed'] and x['diagnostic_only'];samples=0;traces=0;ratios=0;maxerr=0
    for p,h in x['source_sha256'].items():assert sha(ROOT/p)==h
    for m,n in POINTS:
        for rep in range(3):
            p=D/'api'/m/f'N{n}'/f'run{rep}.json';raw=read(p);validate(raw,10,30,True);assert raw['host_api_schema']=='d1-api-v1';assert len(raw['host_api_us'])==7;assert read(p.with_suffix('.process.json'))['exit']==0;assert read(p.with_suffix('.process.json'))['argv'][-7:]==ARGS
            for i,l in enumerate(LABELS):
                rows=raw['host_api_us'][i];assert len(rows)==30
                for j,v in enumerate(rows):assert len(v)==10 and all(math.isfinite(t) and t>=0 for t in v) and sum(v)<=raw['records'][i]['samples_us'][j]+.1
                report=next(z for z in x['rows'] if z['matrix']==m and z['n']==n and z['label']==l)
                for j in range(10):assert math.isclose(statistics.median(v[j] for v in rows),report['host_process_medians_us'][rep][j],rel_tol=1e-12)
                ratio=statistics.median((v[1]+v[3])/w for v,w in zip(rows,raw['records'][i]['samples_us']));assert math.isclose(ratio,report['host_clear_wall_fraction_process_medians'][rep],rel_tol=1e-12);ratios+=1;samples+=30;maxerr=max(maxerr,raw['records'][i]['max_abs_error'])
            traces+=len(raw['trace'])
    assert (samples,traces,ratios)==(3150,4200,105);assert not read(D/'api_final_environment.json')['experiments']
    out={'passed':True,'diagnostic_processes':15,'samples':samples,'trace_calls':traces,'host_component_process_medians_independently_checked':1050,'host_clear_fraction_process_medians_independently_checked':ratios,'max_abs_error':maxerr,'formal_data_changed':False,'interpretation':'host submission time and event stream intervals, not pure device clear or HBM throughput'};save(D/'api_independent_audit.json',out);print(out)
if __name__=='__main__':main()
