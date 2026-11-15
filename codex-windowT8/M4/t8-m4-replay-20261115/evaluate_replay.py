"""Evaluate the frozen M4 model against each real Cora window, then measured replay."""
import csv
import json
import struct
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent;main=root.parent/'t8-m4'
models=json.loads((main/'analysis-v5/model-fits.json').read_text())
assert json.loads((main/'analysis-v5/analysis-status.json').read_text())['final']
manifest=json.loads((root/'replay-manifest.json').read_text());byname={r['name']:r for r in manifest}
journals=sorted((root/'results-blocks-v1').glob('b*-accepted.json'));assert len(journals)==20
observed={}
for file in journals:
    journal=json.loads(file.read_text())
    for group in journal['groups']:
        for r in csv.DictReader((root/group['path']/'timing.csv').open()):
            p=byname[r['case']]
            if (p['dtype'],p['n'])==(group['dtype'],group['N']):
                observed[journal['block'],r['case']]=float(r['us_per_matrix'])
    assert sum(block==journal['block'] for block,name in observed)==40

def read_words(path):
    b=path.read_bytes();return struct.unpack('<'+str(len(b)//4)+'I',b)

results=[];windows_output=[]
for point in manifest:
    name=point['name'];dtype='FP32' if point['dtype'] else 'FP16'
    model=next(r for r in models if (r['dtype'],r['n'],r['cache'],r['merge'],r['pipeline'])==(dtype,point['n'],point['cache'],True,'gmax'))
    cols=json.loads((root/f"{point['order']}-rows.json").read_text())
    cfg=read_words(root/'inputs'/f'{name}.config.bin');off=read_words(root/'inputs'/f'{name}.offsets.bin')
    calls=[0]*len(cols)
    for tile in range(cfg[2]):calls[cfg[24+tile*3]]+=off[tile+1]-off[tile]
    assert sum(map(len,cols))==point['U'] and sum(calls)==point['api_calls']
    segments=[sum(i==0 or c!=v[i-1]+1 for i,c in enumerate(v)) for v in cols]
    assert sum(segments)==point['R']
    measured=np.array([observed[b,name] for b in range(20)])
    entry=dict(case=name,order=point['order'],dtype=dtype,n=point['n'],cache=point['cache'],
               measured_mean_us=float(measured.mean()),measured_median_us=float(np.median(measured)),
               measured_q25_us=float(np.quantile(measured,.25)),measured_q75_us=float(np.quantile(measured,.75)))
    for key,axis in [('R_model',segments),('api_model',calls)]:
        fit=model[key]
        if not fit['identifiable']:
            entry[key]=dict(identifiable=False,reason='rank deficient synthetic design');continue
        beta=np.array(fit['coefficients_by_block'])
        per_window=np.array([[c+a*len(v)+b*count for v,count in zip(cols,axis)] for c,a,b in beta])
        predicted=per_window.sum(axis=1)
        mean=float(predicted.mean());error=abs(mean-entry['measured_mean_us'])/entry['measured_mean_us']
        entry[key]=dict(identifiable=True,predicted_mean_us=mean,predicted_b0_b1_scope='sum over every actual window',
                        relative_error=error,within_15_percent=bool(error<=.15),
                        negative_window_predictions=int(np.sum(per_window.mean(axis=0)<0)),
                        prediction_min_us=float(predicted.min()),prediction_max_us=float(predicted.max()))
        for w,v in enumerate(cols):windows_output.append(dict(case=name,model=key,window=w,U=len(v),R=segments[w],api_calls=calls[w],predicted_us=float(per_window[:,w].mean())))
    b_lo=model['R_model']['ci95_low'][2];b_hi=model['R_model']['ci95_high'][2]
    entry['R_slope_ns_core_equivalent']=dict(mean=model['R_model']['mean'][2]*24000,low=b_lo*24000,high=b_hi*24000)
    entry['R_segment_share_upper']=max(0,b_hi)*point['R']/entry['measured_mean_us']
    entry['G2_model_gate']='PASS' if entry['R_model']['within_15_percent'] and not entry['R_model']['negative_window_predictions'] else 'FAIL'
    results.append(entry)

analysis=root/'analysis-v1';analysis.mkdir(exist_ok=True)
(analysis/'replay-evaluation.json').write_text(json.dumps(results,indent=2))
with (analysis/'window-predictions.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(windows_output[0]));writer.writeheader();writer.writerows(windows_output)
comparisons=[]
for dt in ('FP16','FP32'):
 for n in (16,32,64,128,256):
  for cache in ('hot','cold'):
    a=next(r for r in results if (r['dtype'],r['n'],r['cache'],r['order'])==(dt,n,cache,'B0'))
    b=next(r for r in results if (r['dtype'],r['n'],r['cache'],r['order'])==(dt,n,cache,'B1'))
    qualified=a['G2_model_gate']=='PASS' and b['G2_model_gate']=='PASS'
    slope=a['R_slope_ns_core_equivalent']
    if not qualified:interpretation='no conclusion: model replay gate failed'
    elif slope['low']>0:interpretation='positive slope; amplitude threshold remains user-defined'
    elif slope['low']<=0<=slope['high'] and a['R_segment_share_upper']<.02:interpretation='no measurable segment cost: interval contains zero and upper segment share is below 2 percent'
    else:interpretation='inconclusive: interval/share rule is not decisive; one larger-batch retest required'
    comparison=dict(dtype=dt,n=n,cache=cache,R_model_replay_qualified=qualified,
                    measured_B0_to_B1_reduction=1-b['measured_mean_us']/a['measured_mean_us'],
                    predicted_B0_to_B1_reduction=1-b['R_model']['predicted_mean_us']/a['R_model']['predicted_mean_us'],
                    b_ns_core_equivalent=slope,segment_share_upper=a['R_segment_share_upper'],G2=interpretation)
    comparisons.append(comparison)
(analysis/'B0-B1-comparisons.json').write_text(json.dumps(comparisons,indent=2))
print('REPLAY_EVALUATION_COMPLETE',len(results),'cases','R-model pass',sum(r['R_model']['within_15_percent'] for r in results))
