"""Audit frozen H-V routes, mixed execution evidence and paired raw timings."""
from pathlib import Path
import csv,hashlib,json,math,statistics,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.hv_cases import digest,save,check_split
from rsh.planner import Matrix

def audit()->dict:
    dest=ROOT/'results/hv';state=json.loads((dest/'progress.json').read_text());assert state['state']=='complete' and state['next_version']=='H-C' and state['stop_required']
    assert len(state['completed'])==len(set(state['completed']))==81 and len(state['prepared'])==24
    mf=json.loads((dest/'manifest.json').read_text());snap=dest/'source_snapshot'
    for name,h in mf['source_hashes'].items():assert digest(snap/name)==h,name
    assert digest(snap/'scripts/run_hv.py')==mf['controller_sha256'];assert digest(ROOT/'results/v0/device_binary/rsh_runner')==mf['executable_sha256']
    validation=json.loads((dest/'mixed_validation.json').read_text());assert validation['passed'] and validation['executable_sha256']==mf['executable_sha256']
    csvpath=ROOT/validation['profile_summary'];assert digest(csvpath)==validation['profile_summary_sha256']
    mixed=[r for r in csv.DictReader(csvpath.open()) if r['Op Name']=='rsh_mix'];assert len(mixed)==5
    for r in mixed:assert r['Task Type']=='MIX_AIC' and int(r['Block Num'])==24 and int(r['Mix Block Num'])==48 and float(r['aic_mac_time(us)'])>0 and float(r['aiv_vec_time(us)'])>0
    sm=list((dest/'smoke').glob('*.json'));assert len(sm)==26
    for f in sm:
        x=json.loads(f.read_text());assert x['correctness'] and x['records'][0]['variant']=='H-V'
    null=list((dest/'null_control').glob('*.json'));assert len(null)==9;nullrat=[];nullmed=[]
    for f in null:
        x=json.loads(f.read_text());assert x['correctness'] and x['warmups']==10 and x['repeats']==30;a,b=x['records'];assert a['variant']==b['variant']=='H-V'
        assert len(a['samples_us'])==len(b['samples_us'])==30
        rr=np.asarray(a['samples_us'])/np.asarray(b['samples_us']);nullrat.extend(rr.tolist());nullmed.append(float(np.median(rr)))
    low,high=map(float,np.quantile(nullrat,[.05,.95]));structures=[]
    for name,h in mf['inputs'].items():
        source=ROOT/'inputs'/name;assert digest(source)==h;a=Matrix.load(str(source));pd=dest/'plans'/source.stem;route=json.loads((pd/'routing.json').read_text());s=json.loads((pd/'structure.json').read_text())
        assert digest(pd/'routing.json')==s['routing_sha256'];assert digest(ROOT/'results/v2/orders'/source.stem/'order.bin')==route['order_sha256']==mf['orders'][source.stem]
        check_split(a,route['split']);assert sum(s[k]['rows'] for k in ['G','S','T','Z'])==a.shape[0] and sum(s[k]['nnz'] for k in ['G','S','T','Z'])==len(a.col)
        assert s['G']['rows']==16*s['cube_groups'] and s['S']['rows']+s['T']['rows']==s['aiv_rows'];structures.append(s)
    rows=[];flags=[];maxerr=0;summary=json.loads((dest/'summary.json').read_text());assert len(summary['rows'])==24
    for row in summary['rows']:
        meds=[[],[],[]];samples=[[],[],[]];ratios=[[],[]]
        s=next(s for s in structures if s['matrix']==row['matrix'])
        for rep in range(3):
            x=json.loads((dest/'measurements'/row['matrix']/f'N{row["n"]}'/f'run{rep}.json').read_text());assert x['correctness'] and x['warmups']==10 and x['repeats']==30 and x['interleaving']=='randomized_per_call' and x['mixed_dispatch']=='native_mix_1_2_not_yet_profiled'
            assert [r['variant'] for r in x['records']]==['V0','V2','H-V']
            for i,r in enumerate(x['records']):
                ts=r['samples_us'];assert len(ts)==30 and all(math.isfinite(t) and t>0 for t in ts) and r['valid_rows']==r['m'] and r['n']==row['n'];meds[i].append(float(np.median(ts)));samples[i].extend(ts)
            hv=x['records'][2];assert hv['cube_groups']==s['cube_groups'] and hv['k16_tiles']==s['k16_tiles'] and hv['aiv_rows']==s['aiv_rows'];maxerr=max(maxerr,hv['max_abs_error'])
            for i in range(2):ratios[i].append(float(np.median(np.asarray(x['records'][i]['samples_us'])/np.asarray(hv['samples_us']))))
        r=dict(row)
        for i,v in enumerate(['v0','v2','hv']):
            assert meds[i]==row[v+'_process_medians_us'];r[v+'_iqr_us']=float(np.subtract(*np.quantile(samples[i],[.75,.25])));r[v+'_process_max_min']=max(meds[i])/min(meds[i])
        for i,v in enumerate(['v0','v2']):
            np.testing.assert_allclose(ratios[i],row[v+'_over_hv_per_process'],rtol=1e-12);assert statistics.median(ratios[i])==row[v+'_over_hv'];r[v+'_all_three_faster']=all(t>1 for t in ratios[i]);r[v+'_all_three_slower']=all(t<1 for t in ratios[i]);r[v+'_gain_above_null_envelope']=all(t>high for t in ratios[i])
        for v,folder in [('V0','v0'),('V2','v2'),('H-V','hv')]:
            meta=json.loads((ROOT/f'cases_{folder}'/row['matrix']/f'N{row["n"]}'/v/'metadata.json').read_text());assert meta['coverage']=='full'
            if v=='V0':base=meta
            for key in ['ptr','cols','values','rhs','golden']:assert meta['files_sha256'][key]==base['files_sha256'][key]
        if max(r[v+'_process_max_min'] for v in ['v0','v2','hv'])>1.10:flags.append({'matrix':r['matrix'],'n':r['n'],**{v:r[v+'_process_max_min'] for v in ['v0','v2','hv']}})
        rows.append(r)
    result={'passed':True,'version':'H-V','configurations':24,'paired_processes':72,'null_processes':9,'smoke_checks':26,'samples_per_variant':2160,'hv_max_abs_error':maxerr,'null_ratio_p05_p95':[low,high],'null_process_median_range':[min(nullmed),max(nullmed)],'rows':rows,'structure':structures,'timing_flags':flags,'next_version':'H-C','stop_required':True,'mixed_validation':validation,'threshold_decision':json.loads((dest/'threshold_decision.json').read_text()),'limits':'Full-output controlled backend; approximate RSH-style order. Profile is separate, timings unprofiled. Native MIX_AIC and both pipelines verified; exact overlap fraction unresolved. Raw runner profiling label is frozen, separate validation is authoritative. CPU/H2D excluded from resident timer; no strong external baseline.'}
    for v in ['v0','v2']:
        result[v+'_over_hv_geomean']=math.exp(statistics.mean(math.log(r[v+'_over_hv']) for r in rows))
        for k in ['all_three_faster','all_three_slower','gain_above_null_envelope']:result[v+'_'+k]=sum(r[v+'_'+k] for r in rows)
    if result['threshold_decision'].get('grid_complete'):
        from scripts.audit_hv_grid import audit_grid
        result['grid_audit']=audit_grid()
    save(dest/'local_audit.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['rows','structure','mixed_validation','threshold_decision']},ensure_ascii=False));return result
if __name__=='__main__':audit()
