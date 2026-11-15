"""Recompute M5 statistics from CSV using only Python's standard library.

Usage: python audit_m5_statistics_offline.py PATH_TO_T8_M5
No device, CANN installation, or network is needed. Original analysis is read-only.
"""
from pathlib import Path
import collections, csv, json, math, re, statistics as st, sys

def regression(rows):
    xm=st.mean(x for x,y in rows);ym=st.mean(y for x,y in rows)
    b=sum((x-xm)*(y-ym) for x,y in rows)/sum((x-xm)**2 for x,y in rows)
    a=ym-b*xm
    r2=1-sum((y-a-b*x)**2 for x,y in rows)/sum((y-ym)**2 for x,y in rows)
    return a,b,r2

def mean_curve_r2(blocks):
    batches=collections.defaultdict(list)
    for rows in blocks.values():
        for batch,us in rows:batches[batch].append(us)
    return regression([(batch,st.mean(values)) for batch,values in batches.items()])[2]

def close(a,b):
    assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-11),(a,b)

def audit(root):
    original=collections.defaultdict(lambda:collections.defaultdict(list))
    counts={};registrations={}
    for stage in ('results-blocks','results-quality'):
        reg=json.loads((root/stage/'block-registration.json').read_text())
        valid=[r for r in reg if r['valid']]
        assert sorted(r['block'] for r in valid)==list(range(20))
        counts[stage]=dict(valid_blocks=len(valid),invalid_attempts=len(reg)-len(valid),samples=0)
        registrations[stage]=valid
        target=original if stage=='results-blocks' else collections.defaultdict(lambda:collections.defaultdict(list))
        for record in valid:
            for row in csv.DictReader((root/record['path']/'samples/timing.csv').open()):
                assert int(row['sample'])==record['block']
                name=row['case'];batch=int(row['batch'])
                seg=int(re.search(r'-s(\d+)-',name).group(1))
                assert int(row['api_calls'])==batch*(seg if '-split-' in name else 1)
                # C++ streams wrote us with six significant digits; cycles are exact.
                assert math.isclose(float(row['us']),int(row['cycles'])/50,rel_tol=5.01e-6,abs_tol=1e-9)
                target[name][record['block']].append((batch,float(row['us'])))
                counts[stage]['samples']+=1
        if stage=='results-quality':quality=target
    assert len(original)==688 and counts['results-blocks']['samples']==55040
    assert len(quality)==90 and counts['results-quality']['samples']==7200
    base_bad={name for name,blocks in original.items() if st.mean(regression(v)[2] for v in blocks.values())<.999}
    closure=base_bad|{name.replace('-merge-','-split-') if '-merge-' in name else name.replace('-split-','-merge-') for name in base_bad}
    assert len(base_bad)==59 and closure==set(quality)
    assert closure==set((root/'quality-filter.txt').read_text().splitlines())
    final=dict(original);final.update(quality)
    expected=json.loads((root/'analysis/case-regressions.json').read_text())
    summaries={};fits_on_means={}
    for name,blocks in final.items():
        assert sorted(blocks)==list(range(20)) and all(len(v)==4 for v in blocks.values())
        expected_batches=[256,1024,4096,16384] if name in quality else [64,256,1024,4096]
        assert all(sorted(x for x,y in v)==expected_batches for v in blocks.values())
        slopes=[regression(blocks[i])[1] for i in range(20)]
        mean=st.mean(slopes);half=2.093*st.stdev(slopes)/math.sqrt(20)
        summaries[name]=dict(slopes=slopes,mean=mean,ci_low=mean-half,ci_high=mean+half)
        fits_on_means[name]=mean_curve_r2(blocks)
        for field,value in [('mean_us_per_repeat',mean),('ci_low',mean-half),('ci_high',mean+half)]:close(value,expected[name][field])
    saved_pairs=json.loads((root/'analysis/paired.json').read_text());qualified=[];recomputed=[]
    for pair in saved_pairs:
        name=pair['case'];a=summaries[name];b=summaries[name.replace('-merge-','-split-')]
        diff=[y-x for x,y in zip(a['slopes'],b['slopes'])]
        saved=st.mean(diff);half=2.093*st.stdev(diff)/math.sqrt(20)
        values=dict(merge_us=a['mean'],split_us=b['mean'],speedup=b['mean']/a['mean'],saved_us=saved,saved_ci_low=saved-half,saved_ci_high=saved+half)
        for key,value in values.items():close(value,pair[key])
        result=dict(case=name,segments=pair['segments'],**values);recomputed.append(result)
        if fits_on_means[name]>=.999 and fits_on_means[name.replace('-merge-','-split-')]>=.999:qualified.append(result)
    assert len(saved_pairs)==344 and len(qualified)==343
    assert {r['case'] for r in qualified}=={r['case'] for r in json.loads((root/'analysis/timing-qualified-pairs.json').read_text())}
    groups=[]
    for dtype in ('f16','f32'):
        for api in ('nd','nz'):
            p=[r for r in qualified if r['case'].startswith(dtype+'-'+api+'-') and r['segments']>1]
            groups.append(dict(dtype=dtype,api=api,pairs=len(p),median_speedup=st.median(r['speedup'] for r in p),min_speedup=min(r['speedup'] for r in p),max_speedup=max(r['speedup'] for r in p),pointwise_positive=sum(r['saved_ci_low']>0 for r in p)))
    means_bad={name for name,r2 in fits_on_means.items() if r2<.999}
    assert means_bad=={'f16-nz-merge-s4-h2-gap64-n16'}
    correctness=list(csv.DictReader((root/'results-check/manifest.csv').open()))
    assert len(correctness)==688 and all(r['status']=='PASS' for r in correctness)
    instructions=json.loads((root/'analysis/instruction-verification.json').read_text())
    assert len(instructions)==24 and all(r['transfer_instructions']==(r['segments'] if r['split'] else 1) for r in instructions)
    return dict(status='PASS',scope='Independent standard-library statistical recomputation from formal raw CSV; does not rerun hardware or independently reproduce simulator traces.',counts=counts,correctness_manifest_cases=len(correctness),base_per_block_mean_R2_below_0999=len(base_bad),quality_cases=len(quality),final_case_regressions_compared=688,all_pairs_compared=344,qualified_pairs=343,final_mean_curve_R2_failures=sorted(means_bad),qualified_groups=groups,example=next(r for r in recomputed if r['case']=='f16-nz-merge-s8-h4-gap8-n256'))

if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
    print(json.dumps(audit(root),indent=2))
