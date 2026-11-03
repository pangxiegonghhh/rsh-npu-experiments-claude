"""Run H-V in auditable phases; no H-C/H-Skip execution."""
from pathlib import Path
import argparse,json,os,random,statistics,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.hv_cases import digest,save,smoke_cases,prepare_real

def summarize(dest: Path,files: list[Path])->dict:
    rows=[]
    for f in files:
        for n in [16,64,256]:
            xs=[json.loads((dest/'measurements'/f.stem/f'N{n}'/f'run{r}.json').read_text()) for r in range(3)]
            row={'matrix':f.stem,'n':n,'hv_max_abs_error':max(x['records'][2]['max_abs_error'] for x in xs)}
            for i,v in enumerate(['v0','v2','hv']):
                meds=[statistics.median(x['records'][i]['samples_us']) for x in xs];row[v+'_process_medians_us']=meds;row[v+'_median_us']=statistics.median(meds)
            for i,v in enumerate(['v0','v2']):
                rr=[statistics.median([a/b for a,b in zip(x['records'][i]['samples_us'],x['records'][2]['samples_us'])]) for x in xs];row[v+'_over_hv_per_process']=rr;row[v+'_over_hv']=statistics.median(rr)
            rows.append(row)
    x={'version':'H-V','correctness':True,'configurations':24,'paired_processes':72,'null_processes':9,'rows':rows,'stop_before':'H-C'};save(dest/'summary.json',x);return x

def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['prepare','measure','finish'],required=True);args=ap.parse_args()
    dest=ROOT/'results/hv';dest.mkdir(exist_ok=True);exe=ROOT/'build_v4/rsh_runner';files=sorted((ROOT/'inputs').glob('*.npz'));assert len(files)==8
    paths=sorted(list((ROOT/'npu').glob('*'))+[ROOT/'rsh/planner.py',ROOT/'rsh/prepare.py',ROOT/'scripts/hv_cases.py'])
    manifest={'version':'H-V','source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in paths if p.is_file()},'controller_sha256':digest(Path(__file__)),'executable_sha256':digest(exe),'inputs':{p.name:digest(p) for p in files},'orders':{p.stem:json.loads((ROOT/'results/v2/orders'/p.stem/'structure.json').read_text())['order_sha256'] for p in files},'protocol':{'new_main_version':'H-V','controls':['V0','V2'],'primary_ratio':'V2/H-V','secondary_ratio':'V0/H-V','w':16,'tau_nnz':4,'tau_inc':2,'tail':'AIV','row_ownership':'whole row','order':'reuse measured V2 order.bin','aic_budget':24,'aiv_budget':48,'warmups':10,'samples':30,'processes':3,'seed':20261017,'b_seed':'20261017+N','timer':'full synchronized resident call including clearing/B gather/output restore; excludes CPU/H2D','null':'H-V/H-V: ca-HepTh/N64, web-NotreDame/N64, thermal1/N256; 3 processes','dispatch':'native MIX_AIC_1_2 plus output restoration; profile gate before measurements','stop_before':'H-C','threshold':'conditional follow-up decision before finish, preserve defaults'}}
    mf=dest/'manifest.json'
    if mf.exists():assert json.loads(mf.read_text())==manifest,'Provenance changed; do not overwrite old evidence'
    else:save(mf,manifest)
    sf=dest/'progress.json';state=json.loads(sf.read_text()) if sf.exists() else {'version':'H-V','state':'running','stage':'initial','completed':[],'prepared':[]}
    if state['state']=='complete':print('HV_ALREADY_COMPLETE_STOP_BEFORE_HC',flush=True);return
    def stage(s: str)->None:state.update(state='running',stage=s);save(sf,state);print(s,flush=True)
    def run(cmd: list[str],out: Path,timeout: int=300)->dict:
        out.parent.mkdir(parents=True,exist_ok=True);r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout);out.with_suffix('.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(str(out)+' '+(r.stdout+r.stderr)[-4000:])
        x=json.loads(out.read_text());assert x['correctness'];return x
    try:
        if args.phase=='prepare':
            stage('HV_MIXED_SMOKE');cs=smoke_cases(dest)
            for c in cs:
                for cores in [1,24]:
                    out=dest/'smoke'/f'{c["name"]}_C{cores}.json'
                    if not(out.exists() and json.loads(out.read_text()).get('correctness')):run([str(exe),str(ROOT/c['root']),str(cores),'1','2','20261017',str(out),'H-V'],out,90)
            stage('HV_SMOKE_PASS_26_OF_26')
            for f in files:
                stage('HV_PREPARING_'+f.stem);prepare_real(f,dest)
                for n in [16,64,256]:
                    key=f'{f.stem}/N{n}'
                    if key not in state['prepared']:state['prepared'].append(key)
                save(sf,state)
            state.update(state='prepared',stage='HV_AWAITING_MIXED_EXECUTION_VALIDATION');save(sf,state);print(state['stage'],flush=True)
        elif args.phase=='measure':
            validation=json.loads((dest/'mixed_validation.json').read_text());assert validation['passed'] and validation['executable_sha256']==manifest['executable_sha256']
            assert len(state['prepared'])==24 and len(list((dest/'smoke').glob('*.json')))==26
            stage('HV_NULL_CONTROLS')
            for name,n in [('SNAP_ca-HepTh',64),('SNAP_web-NotreDame',64),('Schmid_thermal1',256)]:
                for rep in range(3):
                    key=f'null/{name}/N{n}/run{rep}'
                    if key in state['completed']:continue
                    out=dest/'null_control'/f'{name}_N{n}_run{rep}.json';run([str(exe),str(ROOT/'cases_hv'/name/f'N{n}'),'24','10','30',str(20261017+rep),str(out),'H-V','H-V'],out)
                    state['completed'].append(key);state['last_completed']=key;save(sf,state)
            stage('HV_PAIRED_MEASUREMENTS');jobs=[(rep,f.stem,n) for rep in range(3) for f in files for n in [16,64,256]];random.Random(20261017).shuffle(jobs)
            for rep,name,n in jobs:
                key=f'paired/{name}/N{n}/run{rep}'
                if key in state['completed']:continue
                out=dest/'measurements'/name/f'N{n}'/f'run{rep}.json';x=run([str(exe),str(ROOT/'cases_hv'/name/f'N{n}'),'24','10','30',str(20261017+rep),str(out),'V0','V2','H-V'],out)
                assert [r['variant'] for r in x['records']]==['V0','V2','H-V'];state['completed'].append(key);state['last_completed']=key;save(sf,state)
                print('HV_PAIRED_DONE',sum(k.startswith('paired/') for k in state['completed']),'/72',key,flush=True)
            summarize(dest,files);state.update(state='default_complete',stage='HV_AWAITING_THRESHOLD_DECISION');save(sf,state);print(state['stage'],flush=True)
        else:
            assert len(state['completed'])==81 and (dest/'threshold_decision.json').exists();summarize(dest,files)
            decision=json.loads((dest/'threshold_decision.json').read_text());assert decision['resolved']
            state.update(state='complete',stage='HV_COMPLETE_STOP_BEFORE_HC',next_version='H-C',stop_required=True);save(sf,state);print(state['stage'],flush=True)
    except BaseException:
        state.update(state='failed',error=traceback.format_exc());save(sf,state);raise
if __name__=='__main__':main()
