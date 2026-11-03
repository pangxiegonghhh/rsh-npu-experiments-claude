"""Independent D3 semantic, raw pair/cost, runtime and transport-input audit."""
from pathlib import Path
import argparse,math,statistics,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));D=ROOT/'results/d3'
from scripts.prepare_d3 import POINTS,LABELS,PROFILE_LABELS,sha,read,save,KEYS
from scripts.run_d3 import validate,protocol,SEED
from rsh.planner import Matrix
CONTRASTS=[('L/F',0,2),('F/J',2,4),('L/J',0,4),('L-B/F-B',1,3),('F-B/J-B',3,5),('L-B/J-B',1,5),('O/J',6,4),('J0/J',7,4),('V2-Z/J',8,4),('L-null',0,1),('F-null',2,3),('J-null',4,5)]

def semantic(m:str)->None:
    a=Matrix.load(str(ROOT/'inputs'/(m+'.npz')));length=np.diff(a.ptr);eligible=np.flatnonzero(length>8);s=np.flatnonzero((length>0)&(length<=8)).tolist();z=np.flatnonzero(length==0).tolist();go=np.fromfile(D/'orders'/m/'F_order.bin',np.int32);lo=np.fromfile(D/'orders'/m/'L_order.bin',np.int32);assert np.array_equal(np.sort(go),np.arange(a.shape[0])) and np.array_equal(np.sort(lo),eligible)
    assert sha(D/'orders'/m/'F_order.bin')==sha(ROOT/'results/v2/orders'/m/'order.bin')
    routes={v:read(D/'plans'/v/m/'routing.json')['split'] for v in ['L','F','J','O','J0']}
    for v,r in routes.items():
        allrows=[x for g in r['groups'] for x in g]+r['residual']+r['tail']+r['zeros'];assert sorted(allrows)==list(range(a.shape[0])) and len(set(allrows))==len(allrows) and all(len(g)==16 for g in r['groups']) and len(r['tail'])<16
        if v!='J0':assert r['zeros']==z and all(length[x]>0 for g in r['groups'] for x in g) and all(length[x]>0 for x in r['residual']+r['tail'])
    for v,order in [('L',lo),('F',go)]:
        seq=[int(x) for x in order if length[x]>8];cut=len(seq)//16*16;r=routes[v];assert r['residual']==s and r['tail']==seq[cut:] and r['groups']==[seq[i:i+16] for i in range(0,cut,16)]
    assert routes['L']['residual']==routes['F']['residual'] and len(routes['L']['tail'])==len(routes['F']['tail'])
    nz=[int(x) for x in go if length[x]>0];cut=len(nz)//16*16;assert routes['O']['residual']==[] and routes['O']['tail']==nz[cut:] and routes['O']['groups']==[nz[i:i+16] for i in range(0,cut,16)]
    supports=[set(a.col[a.ptr[r]:a.ptr[r+1]].tolist()) for r in range(a.shape[0])]
    for v,seq in [('J',nz),('J0',go.tolist())]:
        g=[];sr=[];zz=z.copy() if v=='J' else [];t=[];pos=0
        while pos<len(seq):
            if len(seq)-pos<16:t=seq[pos:];break
            head=seq[pos]
            if not supports[head]:zz.append(head);pos+=1;continue
            win=seq[pos:pos+16];others=set().union(*(supports[x] for x in win[1:]));delta=len(supports[head]-others)
            if len(supports[head])<=8 and delta<4:sr.append(head);pos+=1
            else:g.append(win);pos+=16
        r=routes[v];assert (r['groups'],r['residual'],r['tail'],r['zeros'])==(g,sr,t,zz)
    assert routes['J0']==read(ROOT/'results/d2/plans/t8'/m/'routing.json')['split'];repro=read(D/'orders'/m/'reproduction_aarch64.json');assert repro['global_exact_saved_order'] and repro['L_exact_frozen_order']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full-inputs',action='store_true');a=ap.parse_args();state=read(D/'progress.json');assert state['state']=='complete' and len(set(state['completed']))==240 and len(set(state['profile_completed']))==72
    mf=read(D/'manifest.json')
    for key,name in [('protocol_sha256','protocol.json'),('case_manifest_sha256','case_manifest.json'),('build_sha256','build.json')]:assert sha(D/name)==mf[key]
    for p,h in mf['files'].items():assert sha(ROOT/p)==h and sha(D/'source_snapshot'/p)==h
    b=read(D/'build.json');assert not b['host_recompiled'] and not b['kernel_recompiled'] and b['parent_d2_build_sha256']==sha(ROOT/'results/d2/build.json')
    for k,e in b['programs'].items():assert e==read(ROOT/'results/d2/build.json')['programs'][k] and sha(D/'device_binary'/Path(e['path']).name)==e['sha256']
    for name,e in read(D/'build_objects/index.json').items():assert sha(ROOT/e['saved'])==e['sha256']==b['reused_objects_sha256'][name]
    assert read(D/'zero_probe.json')['passed'] and read(D/'zero_probe.json')['tests']==40
    for m in sorted({m for m,n in POINTS}):semantic(m)
    data=read(D/'analysis.json');assert data['passed'] and data['protocol_sha256']==sha(D/'protocol.json')
    for p,h in data['source_sha256'].items():assert sha(ROOT/p)==h
    pairs=costs=calls=files=metadata=0;mx=0.
    for m,n in POINTS:
        row=next(r for r in data['rows'] if (r['matrix'],r['n'])==(m,n))
        for rep in range(10):
            p=D/'measurements'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30);calls+=len(x['trace']);mx=max(mx,max(r['max_abs_error'] for r in x['records']));assert x['allocation_seed']==((SEED+rep)^0x5A17B39D)
            for key,i,j in CONTRASTS:
                v=statistics.median(t/u for t,u in zip(x['records'][i]['samples_us'],x['records'][j]['samples_us']));assert math.isclose(v,row['contrasts'][key]['process_ratios'][rep],rel_tol=1e-12);pairs+=1
            for suffix in ['before','after']:assert not read(p.with_suffix('.'+suffix+'.json'))['experiments']
            pr=read(p.with_suffix('.process.json'));assert pr['exit']==0 and not pr['event']
        for key,c in row['contrasts'].items():assert math.isclose(math.exp(statistics.mean(map(math.log,c['process_ratios']))),c['geomean'],rel_tol=1e-12)
        for rep in range(3):
            x=read(D/'profile'/m/f'N{n}'/f'run{rep}.json');validate(x,10,30,True);calls+=len(x['trace'])
            for i,label in enumerate(PROFILE_LABELS):
                c=next(t for t in row['costs'] if t['label']==label)
                for key,values in [('event_process_medians_us',x['events'][i]),('api_process_medians_us',x['host_api_us'][i])]:
                    for j in range(len(values[0])):assert statistics.median(t[j] for t in values)==c[key][rep][j];costs+=1
    for key,i,j in CONTRASTS:
        c=data['aggregate'][key]
        for rep in range(10):assert math.isclose(math.exp(statistics.mean(math.log(r['contrasts'][key]['process_ratios'][rep]) for r in data['rows'])),c['process_ratios'][rep],rel_tol=1e-12)
    indices=np.random.default_rng(SEED).integers(0,10,(20000,10))
    for key in ['L/F','F/J','L/J']:
        c=data['aggregate'][key];logs=list(map(math.log,c['process_ratios']));draw=sorted(math.exp(sum(logs[int(i)] for i in idx)/10) for idx in indices)
        for p,expected in zip([.025,.975],c['bootstrap95_conditional']):
            index=(len(draw)-1)*p;lo=int(index);v=draw[lo]+(draw[min(lo+1,len(draw)-1)]-draw[lo])*(index-lo);assert math.isclose(v,expected,rel_tol=1e-12)
    for p,h in read(D/'case_manifest.json')['files'].items():
        if p.endswith('.bin'):
            if a.full_inputs:assert sha(ROOT/p)==h;files+=1
        else:assert sha(ROOT/p)==h;metadata+=1
    if a.full_inputs:
        for root in read(D/'case_manifest.json')['roots']:
            for v in ['L','F','J']:
                base=ROOT/root/v;full=base/'H-V';cfg=list(map(int,(full/'config.txt').read_text().split()));m=cfg[0];rm=np.fromfile(full/'rowmap.bin',np.int32);sr=np.fromfile(full/'srows.bin',np.int32);vg=np.zeros(m,np.uint8);vs=vg.copy();vg[rm[rm>=0]]=1;vs[sr]=1;assert not np.any(vg&vs)
                assert np.array_equal(vg,np.fromfile(base/'G-only/V2/valid.bin',np.uint8)) and np.array_equal(vs,np.fromfile(base/'ST-only/V0/valid.bin',np.uint8))
                for part in ['G-only/V2','ST-only/V0']:
                    for key in ['ptr','cols','values','rhs','golden']:assert sha(base/part/(key+'.bin'))==sha(full/(key+'.bin'))
    smoke=0
    for p in (D/'smoke').glob('*.json'):
        if p.name.endswith(('.before.json','.after.json','.process.json')):continue
        validate(read(p),1,2,p.stem.endswith('_profile'),True);smoke+=1
    assert (pairs,costs,calls,smoke)==(2880,16200,129600,20) and not read(D/'final_environment.json')['experiments']
    out=dict(passed=True,formal_processes=240,formal_samples=64800,profile_processes=72,profile_samples=32400,trace_calls=calls,smoke_processes=smoke,smoke_record_checks=300,zero_guard_tests=40,independent_process_ratios_checked=pairs,independent_cost_medians_checked=costs,binary_files_checked=files,metadata_flag_files_checked=metadata,max_abs_error=mx,semantic_matrices_checked=8,source_and_runtime_unchanged=True,next='D3 stop; recover/audit/save and verified poweroff');save(D/'independent_audit.json',out);print(out)
if __name__=='__main__':main()
