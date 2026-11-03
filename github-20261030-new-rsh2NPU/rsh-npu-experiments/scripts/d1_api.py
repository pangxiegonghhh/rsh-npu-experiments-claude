"""D1 follow-up diagnostic for observed large clear-event intervals, no new method."""
from pathlib import Path
import fcntl,json,math,random,shutil,statistics,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import POINTS,ARGS,LABELS,sha,read,save
from scripts.run_d1 import validate,probe
D=ROOT/'results/d1'
def main():
    lock=(D/'api.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert read(D/'progress.json')['state']=='complete'
    proto={'schema':'d1-api-protocol-v1','trigger':'Event clear intervals unexpectedly dominate. Measure host submission boundaries before attributing to device memory throughput.','formal_data_untouched':True,'points':POINTS,'warm':10,'repeats':30,'processes_per_point':3,'labels':LABELS,'event_instrumentation':True,'primary_speed_claim':False,'stop_after':'D1 only, no new algorithm/threshold; recover and shut down'}
    if (D/'api_protocol.json').exists():assert read(D/'api_protocol.json')==json.loads(json.dumps(proto))
    else:save(D/'api_protocol.json',proto)
    from scripts.prepare_d1_api import main as build
    if not (D/'api_build.json').exists():build()
    exe=ROOT/'build_d1/rsh_runner_api';assert sha(exe)==read(D/'api_build.json')['executable_sha256']
    jobs=[(m,n,r) for r in range(3) for m,n in POINTS];random.Random(2026101803).shuffle(jobs);done=[]
    for m,n,rep in jobs:
        root=ROOT/'cases_d1'/m/f'N{n}';out=D/'api'/m/f'N{n}'/f'run{rep}.json';out.parent.mkdir(parents=True,exist_ok=True)
        if not out.exists():
            pending=out.with_name(out.stem+'.pending-'+str(time.time_ns())+'.json');before=probe();assert not before['experiments'];save(out.with_suffix('.before.json'),before)
            cmd=[str(exe),str(root),'24','10','30',str(20261018+3000+rep),str(pending),*ARGS];p=subprocess.run(cmd,capture_output=True,text=True,timeout=300);pending.with_suffix('.log').write_text(p.stdout+p.stderr);save(out.with_suffix('.after.json'),probe());save(out.with_suffix('.process.json'),{'argv':cmd,'exit':p.returncode});assert p.returncode==0,p.stderr
            x=read(pending);validate(x,10,30,True,root);assert x['host_api_schema']=='d1-api-v1'
            for i,rows in enumerate(x['host_api_us']):
                assert len(rows)==30
                for j,v in enumerate(rows):assert len(v)==10 and all(math.isfinite(t) and t>=0 for t in v) and sum(v)<=x['records'][i]['samples_us'][j]+.1
            pending.replace(out);pending.with_suffix('.log').replace(out.with_suffix('.log'))
        done.append(f'{m}/N{n}/run{rep}');save(D/'api_progress.json',{'state':'measuring','completed':done});print('D1_API',len(done),'/15',done[-1],flush=True)
    summary=[];sources={}
    for m,n in POINTS:
        for i,l in enumerate(LABELS):
            vs=[];ws=[];ev=[];fractions=[]
            for rep in range(3):
                p=D/'api'/m/f'N{n}'/f'run{rep}.json';x=read(p);sources[str(p.relative_to(ROOT))]=sha(p);v=[statistics.median(t[j] for t in x['host_api_us'][i]) for j in range(10)];vs.append(v);ws.append(statistics.median(x['records'][i]['samples_us']));ev.append([statistics.median(t[j] for t in x['events'][i]) for j in range(5)]);fractions.append(statistics.median((v[1]+v[3])/w for v,w in zip(x['host_api_us'][i],x['records'][i]['samples_us'])))
            summary.append({'matrix':m,'n':n,'label':l,'host_fields_us':x['host_api_fields_us'],'host_process_medians_us':vs,'host_median_of_processes_us':[statistics.median(v[j] for v in vs) for j in range(10)],'wall_process_medians_us':ws,'event_process_medians_us':ev,'host_clear_wall_fraction_process_medians':fractions})
    save(D/'api_analysis.json',{'passed':True,'diagnostic_only':True,'processes':15,'samples':3150,'rows':summary,'source_sha256':sources,'limit':'Host submission calls can include runtime blocking/work. Event intervals include stream gaps while host submits. Neither measures pure HBM bandwidth or pure CPU arithmetic. Added clocks/events perturb timing.'});save(D/'api_progress.json',{'state':'complete','completed':done,'stop_before_D2':True})
    for name in ['scripts/prepare_d1_api.py','scripts/d1_api.py','diagnostics/d1/api_runner.cpp']:
        p=ROOT/name;q=D/'api_source_snapshot'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    save(D/'api_final_environment.json',probe());assert not read(D/'api_final_environment.json')['experiments'];print('D1_API_COMPLETE',flush=True)
if __name__=='__main__':main()
