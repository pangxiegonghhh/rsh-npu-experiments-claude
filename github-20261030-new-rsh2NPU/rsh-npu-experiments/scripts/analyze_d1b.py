"""Offline D1b within-process backend comparison and separate API/event breakdown."""
from pathlib import Path
import csv,math,random,statistics,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1b import POINTS,LABELS,sha,read,save
from scripts.run_d1b import validate
from scripts.analyze_d0 import gm,quantile
D=ROOT/'results/d1b'
CONTRASTS=[('Old-V0/New-V0',0,1),('Old-V2/New-V2',2,3),('Old-V2-Z/New-V2-Z',4,5),('Old-HV/New-HV-A',6,7),('Old-HV/New-HV-B',6,8),('New-V0/New-HV-A',1,7),('New-V2/New-HV-A',3,7),('New-V2-Z/New-HV-A',5,7),('New-V2/New-V2-Z',3,5),('New-HV-A/New-HV-B',7,8)]
def interval(x):
    rng=random.Random(20261019);logs=list(map(math.log,x));n=len(x);draws=[math.exp(sum(logs[rng.randrange(n)] for _ in range(n))/n) for _ in range(20000)];return [quantile(draws,.025),quantile(draws,.975)]
def main():
    rows=[];process=[];sources={}
    for m,n in POINTS:
        ratios={k:[] for k,_,_ in CONTRASTS};latency={l:[] for l in LABELS};maxerr=0.
        for rep in range(10):
            p=D/'measurements'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30);sources[str(p.relative_to(ROOT))]=sha(p);arrays=[r['samples_us'] for r in x['records']]
            for i,l in enumerate(LABELS):
                median=statistics.median(arrays[i]);latency[l].append(median);process.append({'matrix':m,'n':n,'rep':rep,'label':l,'median_us':median,'max_abs_error':x['records'][i]['max_abs_error']});maxerr=max(maxerr,x['records'][i]['max_abs_error'])
            for key,i,j in CONTRASTS:ratios[key].append(statistics.median(a/b for a,b in zip(arrays[i],arrays[j])))
            for suffix in ['before','after','process']:
                q=p.with_suffix('.'+suffix+'.json');sources[str(q.relative_to(ROOT))]=sha(q)
        guard=math.exp(quantile([abs(math.log(v)) for v in ratios['New-HV-A/New-HV-B']],.95));cs={}
        for key,_,_ in CONTRASTS:
            v=ratios[key];g=gm(v);ci=interval(v);faster=sum(t>1 for t in v);cs[key]={'process_ratios':v,'geomean':g,'bootstrap95_conditional':ci,'faster_count':faster,'clear_positive_descriptive':ci[0]>1 and g>guard and faster>=8}
        costs=[]
        for i,l in enumerate(LABELS):
            evs=[];apis=[];walls=[];clear_fraction=[]
            for rep in range(3):
                p=D/'profile'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30,True);sources[str(p.relative_to(ROOT))]=sha(p);evs.append([statistics.median(t[j] for t in x['events'][i]) for j in range(5)]);apis.append([statistics.median(t[j] for t in x['host_api_us'][i]) for j in range(10)]);walls.append(statistics.median(x['records'][i]['samples_us']));clear_fraction.append(statistics.median((t[1]+t[3])/w for t,w in zip(x['host_api_us'][i],x['records'][i]['samples_us'])))
            costs.append({'label':l,'event_fields_us':x['event_fields_us'],'host_fields_us':x['host_api_fields_us'],'event_process_medians_us':evs,'api_process_medians_us':apis,'profile_wall_process_medians_us':walls,'event_median_us':[statistics.median(t[j] for t in evs) for j in range(5)],'api_median_us':[statistics.median(t[j] for t in apis) for j in range(10)],'clear_api_wall_process_fractions':clear_fraction})
        rows.append({'matrix':m,'n':n,'contrasts':cs,'formal_process_medians_us':latency,'null_guard':guard,'costs':costs,'max_abs_error':maxerr})
    out={'passed':True,'schema':'d1b-analysis-v1','formal_processes':50,'formal_samples':13500,'formal_trace_calls':18000,'profile_processes':15,'profile_samples':4050,'profile_trace_calls':5400,'rows':rows,'process_records':process,'source_sha256':sources,'limits':['Five selected points in one device session; process bootstrap ranges are exploratory conditional intervals, not matrix/hardware-population inference.','Same unified new host performs old/runtime and new/AIV clearing branches with same compute objects. Absolute times are not spliced with D1.','Formal timings have no device events; API/event profile is separate and perturbs execution. Event spans include host submission gaps; host API/sync may contain runtime work or waits.','Both output and packed are fully zeroed whenever original did so. No clear removal/fusion, routing/reorder/threshold change.','No strong sparse-library baseline, pipeline optimization, D2 or D3. Backend improvement alone is not research novelty.']};save(D/'local_audit.json',out)
    with (D/'process_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(process[0]));w.writeheader();w.writerows(process)
    lines=['# D1b：公共清零后端验证','','只替换清零实现；两次必要清零的范围与次数不变，计算内核/组成员/路由/4/2均不变。50个独立进程、各10预热30采样，同进程随机交错旧/新后端9记录。正式计时未插设备事件。','','| 点 | 旧/新V0 | 旧/新V2 | 旧/新V2-Z | 旧/新HV-A | 新V0/新HV-A | 新V2/新HV-A | 新V2-Z/新HV-A | 新V2/新V2-Z | 空对照 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    keys=['Old-V0/New-V0','Old-V2/New-V2','Old-V2-Z/New-V2-Z','Old-HV/New-HV-A','New-V0/New-HV-A','New-V2/New-HV-A','New-V2-Z/New-HV-A','New-V2/New-V2-Z','New-HV-A/New-HV-B']
    for r in rows:lines.append(f"| {r['matrix']}/N{r['n']} | "+' | '.join(f"{r['contrasts'][k]['geomean']:.4f}" for k in keys)+' |')
    lines+=['','比值>1表示分母更快。先取每进程30个迭代配对比中位数，再做10进程几何平均。全部原始慢点保留，不以历史绝对时间拼接加速。','','## 逐进程配对比与条件区间','']
    for r in rows:
        lines += [f"### {r['matrix']} / N{r['n']}",'',f"空对照描述性保护值：{r['null_guard']:.6f}",'']
        for k,c in r['contrasts'].items():
            ci=c['bootstrap95_conditional'];lines.append(f"- {k}: {c['geomean']:.6f}, [{ci[0]:.6f},{ci[1]:.6f}], {c['faster_count']}/10；清晰描述性正信号={c['clear_positive_descriptive']}。进程比："+', '.join(f'{v:.6f}' for v in c['process_ratios']))
        lines.append('')
    lines+=['## 分项诊断（15独立进程，另存）','','单位μs，先取每进程中位数，再取三个进程中位数。事件分项分别取中位数，不要求相加为总中位数。空操作事件间隔是插桩开销。主核包含B收集，final sync不是纯设备时间。','','| 点/标签 | 输出清零事件区间 | packed清零事件区间 | 主核事件区间 | 恢复事件区间 | span | 输出清零API | packed清零API | 主核launch | sync |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        for c in r['costs']:
            e=c['event_median_us'];h=c['api_median_us'];lines.append(f"| {r['matrix']}/N{r['n']} {c['label']} | "+' | '.join(f'{v:.3f}' for v in e+[h[1],h[3],h[5],h[9]])+' |')
    lines+=['','## 解释边界','']+['- '+v for v in out['limits']]
    (D/'分析.md').write_text('\n'.join(lines)+'\n');print({'passed':True,'formal':50,'profile':15,'max_abs_error':max(r['max_abs_error'] for r in rows)})
if __name__=='__main__':main()
