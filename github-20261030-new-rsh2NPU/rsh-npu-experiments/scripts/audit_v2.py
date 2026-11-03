"""Recompute V2 paired statistics; retain all samples and disclose noise."""
from pathlib import Path
import hashlib,json,math,statistics
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit():
    dest=ROOT/'results/v2';state=json.loads((dest/'progress.json').read_text());assert state['state']=='complete' and state['stop_required'] and state['next_version']=='H-V'
    assert len(state['completed'])==len(set(state['completed']))==81 and len(state['prepared'])==24
    manifest=json.loads((dest/'manifest.json').read_text());source=dest/'source_snapshot'
    for p,h in manifest['source_hashes'].items():assert digest(source/p)==h,p
    assert digest(source/'scripts/run_v2.py')==manifest['controller_sha256']
    assert digest(ROOT/'results/v0/device_binary/rsh_runner')==manifest['executable_sha256']
    for p,h in manifest['inputs'].items():assert digest(ROOT/'inputs'/p)==h
    smoke=list((dest/'smoke').glob('*.json'));assert len(smoke)==20
    sr=json.loads((dest/'smoke_preparation.json').read_text());assert sr['passed']
    for r in sr['cases']:assert r['cpu_correct'] and r['order']!=list(range(r['m']))
    for p in smoke:
        x=json.loads(p.read_text());assert x['correctness'] and x['records'][0]['variant']=='V2'
    null=list((dest/'null_control').glob('*.json'));assert len(null)==9
    nullratios=[];nullmed=[]
    for p in null:
        x=json.loads(p.read_text());assert x['correctness'] and x['warmups']==10 and x['repeats']==30
        a,b=x['records'];assert a['variant']==b['variant']=='V1'
        assert len(a['samples_us'])==len(b['samples_us'])==30
        ratios=np.asarray(a['samples_us'])/np.asarray(b['samples_us']);nullratios.extend(ratios);nullmed.append(float(np.median(ratios)))
    low,high=map(float,np.quantile(nullratios,[.05,.95]));summary=json.loads((dest/'summary.json').read_text());assert len(summary['rows'])==24
    rows=[];structures=[];flags=[];maxerr=0
    for name in manifest['inputs']:
        od=dest/'orders'/Path(name).stem;s=json.loads((od/'structure.json').read_text());order=np.fromfile(od/'order.bin',np.int32)
        assert digest(od/'order.bin')==s['order_sha256'] and s['input_sha256']==manifest['inputs'][name]
        assert np.array_equal(np.sort(order),np.arange(s['m']));structures.append(s)
    for row in summary['rows']:
        samples=[[],[],[]];meds=[[],[],[]];ratios=[[],[]]
        for rep in range(3):
            x=json.loads((dest/'measurements'/row['matrix']/f'N{row["n"]}'/f'run{rep}.json').read_text())
            assert x['correctness'] and x['warmups']==10 and x['repeats']==30 and x['interleaving']=='randomized_per_call' and x['mixed_dispatch']=='not_used'
            assert x['cores_aic']==24 and x['cores_aiv']==48 and [r['variant'] for r in x['records']]==['V0','V1','V2']
            for i,r in enumerate(x['records']):
                ts=r['samples_us'];assert r['valid_rows']==r['m'] and r['n']==row['n'] and len(ts)==30 and all(math.isfinite(v) and v>0 for v in ts)
                if i==0:assert r['cube_groups']==r['k16_tiles']==0 and r['aiv_rows']==r['m']
                else:assert r['cube_groups']==(r['m']+15)//16 and r['aiv_rows']==0
                meds[i].append(float(np.median(ts)));samples[i].extend(ts)
            maxerr=max(maxerr,x['records'][2]['max_abs_error'])
            for i in range(2):ratios[i].append(float(np.median(np.asarray(x['records'][i]['samples_us'])/np.asarray(x['records'][2]['samples_us']))))
        r=dict(row)
        for i,v in enumerate(['v0','v1','v2']):
            assert meds[i]==row[v+'_process_medians_us']
            r[v+'_iqr_us']=float(np.subtract(*np.quantile(samples[i],[.75,.25])))
            r[v+'_process_max_min']=max(meds[i])/min(meds[i])
        for i,v in enumerate(['v0','v1']):
            np.testing.assert_allclose(ratios[i],row[v+'_over_v2_per_process'],rtol=1e-12)
            assert statistics.median(ratios[i])==row[v+'_over_v2']
            r[v+'_all_three_faster']=all(t>1 for t in ratios[i]);r[v+'_all_three_slower']=all(t<1 for t in ratios[i]);r[v+'_gain_above_null_envelope']=all(t>high for t in ratios[i])
        for v in ['V0','V1','V2']:
            meta=json.loads((ROOT/f'cases_{v.lower()}'/row['matrix']/f'N{row["n"]}'/v/'metadata.json').read_text())
            assert meta['coverage']=='full'
            if v=='V0':base=meta
            for key in ['ptr','cols','values','rhs','golden']:assert meta['files_sha256'][key]==base['files_sha256'][key]
        if max(r[v+'_process_max_min'] for v in ['v0','v1','v2'])>1.10:flags.append({'matrix':r['matrix'],'n':r['n'],**{v:r[v+'_process_max_min'] for v in ['v0','v1','v2']}})
        rows.append(r)
    result={'passed':True,'version':'V2','configurations':24,'paired_processes':72,'null_processes':9,'smoke_checks':20,'v2_samples':2160,'control_samples_each':2160,'null_samples':540,'v2_max_abs_error':maxerr,'null_ratio_p05_p95':[low,high],'null_process_median_range':[min(nullmed),max(nullmed)],'rows':rows,'structure':structures,'timing_flags':flags,'limits':'Controlled backend, approximate RSH-style ordering; null envelope is descriptive, not significance; no Neutron/library comparison; preprocessing excluded from resident-call timer.','stop_required':True,'next_version':'H-V'}
    for v in ['v0','v1']:
        result[v+'_over_v2_geomean']=math.exp(statistics.mean(math.log(r[v+'_over_v2']) for r in rows))
        for k in ['all_three_faster','all_three_slower','gain_above_null_envelope']:result[v+'_'+k]=sum(r[v+'_'+k] for r in rows)
    (dest/'local_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['rows','structure']},ensure_ascii=False));return result
if __name__=='__main__':audit()
