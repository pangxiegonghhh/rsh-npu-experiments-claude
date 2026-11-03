"""D3 fixed process-unit analysis; no threshold adaptation or sample exclusions."""
from pathlib import Path
import csv,itertools,math,statistics,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));D=ROOT/'results/d3'
from scripts.prepare_d3 import POINTS,LABELS,PROFILE_LABELS,sha,read,save
from scripts.run_d3 import validate,SEED
CONTRASTS=[('L/F',0,2),('F/J',2,4),('L/J',0,4),('L-B/F-B',1,3),('F-B/J-B',3,5),('L-B/J-B',1,5),('O/J',6,4),('J0/J',7,4),('V2-Z/J',8,4),('L-null',0,1),('F-null',2,3),('J-null',4,5)]
PRIMARY=['L/F','F/J','L/J'];ALTERNATE={'L/F':'L-B/F-B','F/J':'F-B/J-B','L/J':'L-B/J-B'}
def gm(v):return math.exp(statistics.mean(map(math.log,v)))
def interval(v):
    a=np.log(np.array(v,np.float64));ix=np.random.default_rng(SEED).integers(0,len(a),(20000,len(a)));draw=np.exp(a[ix].mean(axis=1));return np.quantile(draw,[.025,.975]).tolist()
def sign_test(v):
    pos=sum(x>1 for x in v);neg=sum(x<1 for x in v);n=pos+neg
    return min(1.,2*sum(math.comb(n,i) for i in range(min(pos,neg)+1))/2**n) if n else 1.
def summary(v):return dict(process_ratios=v,geomean=gm(v),bootstrap95_conditional=interval(v),faster_count=sum(x>1 for x in v),mean=statistics.mean(v),std=statistics.stdev(v),sign_test_two_sided=sign_test(v))
def guard(cs):return max(1.,*[math.exp(float(np.quantile([abs(math.log(v)) for v in cs[k]],.95))) for k in ['L-null','F-null','J-null']])
def holm(items):
    ordered=sorted(items,key=lambda c:c['sign_test_two_sided']);prev=0
    for rank,c in enumerate(ordered):prev=max(prev,min(1.,(len(items)-rank)*c['sign_test_two_sided']));c['sign_test_holm']=prev

def identities()->dict:
    result={}
    for m,_ in POINTS:
        if m in result:continue
        h={v:{k:sha(D/'plans'/v/m/'full'/(k+'.bin')) for k in ['cube_ptr','colref','tiles','rowmap','srows']} for v in ['L','F','J','O','J0','V2-Z']};same={}
        for key,a,b in [('L/F','L','F'),('F/J','F','J'),('L/J','L','J'),('O/J','O','J'),('J0/J','J0','J')]:same[key]=h[a]==h[b]
        same['V2-Z/J']=False # Cube-only and MIX dispatch differ even when arrays coincide.
        result[m]=dict(sha256=h,identical_execution=same)
    return result

def main():
    rows=[];process=[];sources={};ident=identities()
    for m,n in POINTS:
        ratios={k:[] for k,_,_ in CONTRASTS};latency={l:[] for l in LABELS};prep={l:[] for l in LABELS};first={l:[] for l in LABELS};maxerr=0.
        for rep in range(10):
            p=D/'measurements'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30);sources[str(p.relative_to(ROOT))]=sha(p);arrays=[r['samples_us'] for r in x['records']]
            for i,l in enumerate(LABELS):
                value=statistics.median(arrays[i]);latency[l].append(value);prep[l].append(x['records'][i]['device_prepare_us']);first[l].append(x['records'][i]['first_us']);process.append(dict(matrix=m,n=n,rep=rep,label=l,median_us=value,allocation_position=x['allocation_order'].index(i),max_abs_error=x['records'][i]['max_abs_error']));maxerr=max(maxerr,x['records'][i]['max_abs_error'])
            for key,i,j in CONTRASTS:ratios[key].append(statistics.median(a/b for a,b in zip(arrays[i],arrays[j])))
            for suffix in ['before','after','process']:
                q=p.with_suffix('.'+suffix+'.json');sources[str(q.relative_to(ROOT))]=sha(q)
        g=guard(ratios);cs={k:summary(v) for k,v in ratios.items()}
        for key in PRIMARY:
            c=cs[key];c['identical_execution']=ident[m]['identical_execution'][key];c['descriptive_positive']=c['bootstrap95_conditional'][0]>1 and c['geomean']>g and c['faster_count']>=8 and cs[ALTERNATE[key]]['geomean']>1 and not c['identical_execution'];c['clear_regression']=c['bootstrap95_conditional'][1]<1 and c['geomean']<1/g and sum(v<1 for v in c['process_ratios'])>=8 and not c['identical_execution']
        costs=[]
        for i,l in enumerate(PROFILE_LABELS):
            ev=[];apis=[];walls=[];masks=[]
            for rep in range(3):
                p=D/'profile'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30,True);sources[str(p.relative_to(ROOT))]=sha(p);ev.append([statistics.median(t[j] for t in x['events'][i]) for j in range(5)]);apis.append([statistics.median(t[j] for t in x['host_api_us'][i]) for j in range(10)]);walls.append(statistics.median(x['records'][i]['samples_us']));masks.append(x['records'][i]['valid_rows'])
            costs.append(dict(label=l,valid_rows=masks[0],empty_valid_scope=masks[0]==0,event_process_medians_us=ev,api_process_medians_us=apis,wall_process_medians_us=walls,event_median_us=[statistics.median(t[j] for t in ev) for j in range(5)],api_median_us=[statistics.median(t[j] for t in apis) for j in range(10)],event_fields_us=x['event_fields_us'],host_fields_us=x['host_api_fields_us']))
        rows.append(dict(matrix=m,n=n,contrasts=cs,null_guard=g,formal_process_medians_us=latency,device_prepare_us=prep,first_us=first,costs=costs,max_abs_error=maxerr))
    holm([r['contrasts'][k] for r in rows for k in PRIMARY]);aggregate={k:[gm([r['contrasts'][k]['process_ratios'][rep] for r in rows]) for rep in range(10)] for k,_,_ in CONTRASTS};ag={k:summary(v) for k,v in aggregate.items()};g=guard(aggregate);holm([ag[k] for k in PRIMARY])
    for key in PRIMARY:
        c=ag[key];matrices=sorted({r['matrix'] for r in rows if r['contrasts'][key]['descriptive_positive']});regressions=[f"{r['matrix']}/N{r['n']}" for r in rows if r['contrasts'][key]['clear_regression']];c.update(descriptive_positive=c['bootstrap95_conditional'][0]>1 and c['geomean']>g and c['faster_count']>=8 and ag[ALTERNATE[key]]['geomean']>1 and any(not ident[m]['identical_execution'][key] for m,_ in POINTS),positive_matrices=matrices,clear_regression_points=regressions);c['workflow_followup_signal']=c['descriptive_positive'] and len(matrices)>=2
    out=dict(schema='d3-analysis-v1',passed=True,rows=rows,aggregate=ag,aggregate_null_guard=g,formal_processes=240,formal_samples=64800,formal_trace_calls=86400,profile_processes=72,profile_samples=32400,profile_trace_calls=43200,process_records=process,layout_identity=ident,source_sha256=sources,protocol_sha256=sha(D/'protocol.json'),limits=['Fixed eight previously seen matrices/three N and one device session; intervals/process sign tests are exploratory conditional summaries.','L/F share exact S, zero exclusion and AIV tail policy, but graph domain/weights/sampling local IDs and tail members may differ. F/J changes routing, grouping, S order and tails.','All L/F/J/O full output and common zero policy; J0 and V2-Z references reveal other changes, not Neutron or a strong sparse-library baseline.','Resident synchronized full-call timing, CPU preprocessing and host prepare/first call separate. device_prepare_us includes file/alloc/H2D and excludes some setup; no complete application E2E or q amortization claim.','Separate profile has instrumentation; G/ST branch timings cannot sum/max as real overlap.','No threshold tuning, no sample deletion, no long-row split; no originality/publication readiness conclusion.']);save(D/'analysis.json',out)
    with (D/'process_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(process[0]));w.writeheader();w.writerows(process)
    lines=['# D3 L/F/J完整调用分析','','比值>1表示分母更快。每进程30个配对比中位数，10进程几何平均；区间仅为单设备会话下的进程条件bootstrap。','','| 点 | L/F | F/J | L/J | O/J | J0/J | V2-Z/J | 空对照保护 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['matrix']}/N{r['n']} | "+' | '.join(f"{r['contrasts'][k]['geomean']:.6f}" for k in ['L/F','F/J','L/J','O/J','J0/J','V2-Z/J'])+f" | {r['null_guard']:.6f} |")
    lines+=['','## 综合主比较','']
    for key in PRIMARY:lines.append(f"- {key}: {ag[key]}")
    lines+=['','## 边界','']+['- '+x for x in out['limits']];(D/'分析.md').write_text('\n'.join(lines)+'\n');print(dict(passed=True,primary={k:ag[k] for k in PRIMARY},guard=g),flush=True)
if __name__=='__main__':main()
