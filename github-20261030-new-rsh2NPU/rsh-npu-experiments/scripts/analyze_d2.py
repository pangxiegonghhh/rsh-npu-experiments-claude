"""D2 frozen decision and reproducible process-level descriptive analysis."""
from pathlib import Path
import argparse,csv,math,random,statistics,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d2 import DEV,EVAL,LABELS,PROFILE_LABELS,sha,read,save
from scripts.run_d2 import validate,protocol
from scripts.analyze_d0 import gm,quantile
D=ROOT/'results/d2';SEED=20261029
CONTRASTS=[('T4-A/T8-A',0,2),('T4-B/T8-B',1,3),('T4-A/T8-B',0,3),('T4-B/T8-A',1,2),('T4-A/T4-B',0,1),('T8-A/T8-B',2,3),('V0/T4-A',4,0),('V0/T8-A',4,2),('V2/T4-A',5,0),('V2/T8-A',5,2)]
def interval(x):
    rng=random.Random(SEED);logs=list(map(math.log,x));n=len(x);draws=[math.exp(sum(logs[rng.randrange(n)] for _ in range(n))/n) for _ in range(20000)];return [quantile(draws,.025),quantile(draws,.975)]
def sign_test(v):
    pos=sum(x>1 for x in v);neg=sum(x<1 for x in v);n=pos+neg
    return min(1.,2*sum(math.comb(n,k) for k in range(min(pos,neg)+1))/2**n) if n else 1.
def guard(cs):return max(1.,*[math.exp(quantile([abs(math.log(x)) for x in cs[k]],.95)) for k in ['T4-A/T4-B','T8-A/T8-B']])
def summary(v):return dict(process_ratios=v,geomean=gm(v),bootstrap95_conditional=interval(v),faster_count=sum(x>1 for x in v),sign_test_two_sided=sign_test(v))
def main(scope):
    points=[(m,64) for m in DEV] if scope=='dev' else [(m,n) for m in EVAL for n in [16,64,256]];rows=[];process=[];sources={}
    for m,n in points:
        ratios={k:[] for k,_,_ in CONTRASTS};latency={l:[] for l in LABELS};maxerr=0.
        for rep in range(10):
            p=D/scope/'measurements'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30);sources[str(p.relative_to(ROOT))]=sha(p);arrays=[r['samples_us'] for r in x['records']]
            for i,l in enumerate(LABELS):
                v=statistics.median(arrays[i]);latency[l].append(v);process.append(dict(matrix=m,n=n,rep=rep,label=l,median_us=v,max_abs_error=x['records'][i]['max_abs_error'],allocation_position=x['allocation_order'].index(i)));maxerr=max(maxerr,x['records'][i]['max_abs_error'])
            for key,i,j in CONTRASTS:ratios[key].append(statistics.median(a/b for a,b in zip(arrays[i],arrays[j])))
            for suffix in ['before','after','process']:
                q=p.with_suffix('.'+suffix+'.json');sources[str(q.relative_to(ROOT))]=sha(q)
        g=guard(ratios);cs={k:summary(v) for k,v in ratios.items()};primary=cs['T4-A/T8-A'];regression=primary['bootstrap95_conditional'][1]<1 and primary['geomean']<1/g and sum(v<1 for v in primary['process_ratios'])>=8
        costs=[]
        for i,l in enumerate(PROFILE_LABELS):
            evs=[];apis=[];walls=[];masks=[]
            for rep in range(3):
                p=D/scope/'profile'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30,True);sources[str(p.relative_to(ROOT))]=sha(p);evs.append([statistics.median(t[j] for t in x['events'][i]) for j in range(5)]);apis.append([statistics.median(t[j] for t in x['host_api_us'][i]) for j in range(10)]);walls.append(statistics.median(x['records'][i]['samples_us']));masks.append(x['records'][i]['valid_rows'])
            costs.append(dict(label=l,valid_rows=masks[0],empty_valid_scope=masks[0]==0,event_fields_us=x['event_fields_us'],host_fields_us=x['host_api_fields_us'],event_process_medians_us=evs,api_process_medians_us=apis,wall_process_medians_us=walls,event_median_us=[statistics.median(t[j] for t in evs) for j in range(5)],api_median_us=[statistics.median(t[j] for t in apis) for j in range(10)]))
        rows.append(dict(matrix=m,n=n,contrasts=cs,formal_process_medians_us=latency,null_guard=g,clear_dev_regression=regression,costs=costs,max_abs_error=maxerr))
    order=sorted(range(len(rows)),key=lambda i:rows[i]['contrasts']['T4-A/T8-A']['sign_test_two_sided']);prev=0
    for rank,i in enumerate(order):
        c=rows[i]['contrasts']['T4-A/T8-A'];prev=max(prev,min(1.,(len(rows)-rank)*c['sign_test_two_sided']));c['sign_test_holm_secondary_family']=prev
    aggregate={k:[gm([r['contrasts'][k]['process_ratios'][rep] for r in rows]) for rep in range(10)] for k,_,_ in CONTRASTS};ag={k:summary(v) for k,v in aggregate.items()};g=guard(aggregate)
    out=dict(schema='d2-analysis-v1',scope=scope,passed=True,formal_processes=len(points)*10,formal_samples=len(points)*10*30*6,profile_processes=len(points)*3,profile_samples=len(points)*3*30*10,rows=rows,aggregate=ag,aggregate_null_guard=g,process_records=process,source_sha256=sources,protocol_sha256=sha(D/'protocol.json'),limits=['Resident synchronized full call only; no fresh reordering/H2D amortization or application E2E.','Exploratory single-device single-session conditional process bootstrap, 10 process aggregates; matrices fixed and previously seen. Within-process samples are not independent N=300.','Duplicate allocation controls, randomized construction and timed order mitigate but cannot eliminate runtime/memory placement bias.','Separate profile has instrumentation; event intervals include host gaps, API/sync may wait. G/ST-only are masked diagnostic paths with full clears; cannot sum/max as MIX overlap.','No strong optimized sparse-library or Neutron baseline and no novelty conclusion. No D3.'])
    save(D/(scope+'_analysis.json'),out)
    if scope=='dev':
        c=ag['T4-A/T8-A'];conditions=dict(primary_ci_lower_above_one=c['bootstrap95_conditional'][0]>1,primary_exceeds_guard=c['geomean']>g,at_least_eight_process_aggregates_faster=c['faster_count']>=8,alternate_copies_direction=ag['T4-B/T8-B']['geomean']>1,no_clear_dev_regression=not any(r['clear_dev_regression'] for r in rows));choice=dict(schema='d2-threshold-selection-v1',selected_thresholds=[8,4] if all(conditions.values()) else [4,2],conditions=conditions,primary=c,aggregate_null_guard=g,alternate=ag['T4-B/T8-B'],dev_analysis_sha256=sha(D/'dev_analysis.json'),protocol_sha256=sha(D/'protocol.json'),backend_selection_sha256=sha(ROOT/'results/d1b/backend_selection.json'),eval_allowed=all(conditions.values()))
        p=D/'threshold_selection.json'
        if p.exists():assert read(p)==choice
        else:save(p,choice)
    with (D/(scope+'_process_summary.csv')).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(process[0]));w.writeheader();w.writerows(process)
    lines=[f'# D2 {scope} 分析','','比值4/2时间÷8/4时间，大于1表示8/4更快。每进程30次配对比中位数，10进程几何平均。条件区间和符号检验仅限本次设备会话。','', '| 矩阵/N | 4/2÷8/4 | 条件95%区间 | 快进程数 | 保护值 | 副本B比 | Holm p（探索） |','|---|---:|---|---:|---:|---:|---:|']
    for r in rows:
        c=r['contrasts']['T4-A/T8-A'];ci=c['bootstrap95_conditional'];lines.append(f"| {r['matrix']}/N{r['n']} | {c['geomean']:.6f} | [{ci[0]:.6f}, {ci[1]:.6f}] | {c['faster_count']}/10 | {r['null_guard']:.6f} | {r['contrasts']['T4-B/T8-B']['geomean']:.6f} | {c['sign_test_holm_secondary_family']:.6f} |")
    c=ag['T4-A/T8-A'];lines+=['',f"综合几何平均：{c['geomean']:.6f}；条件区间{c['bootstrap95_conditional']}；{c['faster_count']}/10，综合保护值{g:.6f}。"]
    if scope=='dev':lines+=['',f"冻结选择：{choice['selected_thresholds']}；条件：{conditions}"]
    lines+=['','## 边界','']+['- '+s for s in out['limits']];(D/(scope+'_分析.md')).write_text('\n'.join(lines)+'\n');print(dict(scope=scope,aggregate=c,guard=g,selected=read(D/'threshold_selection.json')['selected_thresholds']),flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--scope',choices=['dev','eval'],required=True);main(a.parse_args().scope)
