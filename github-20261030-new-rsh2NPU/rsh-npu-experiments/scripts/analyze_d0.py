"""Audit and summarize D0 from raw four-record JSON; offline, no device work."""
from __future__ import annotations
import csv,hashlib,json,math,random,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_d0 import POINTS,validate,read,save,sha
DEST=ROOT/'results/d0'
def gm(x:list[float])->float:return math.exp(statistics.mean(math.log(a) for a in x))
def quantile(x:list[float],p:float)->float:
    a=sorted(x);pos=(len(a)-1)*p;lo=int(pos);hi=min(lo+1,len(a)-1);return a[lo]+(pos-lo)*(a[hi]-a[lo])
def interval(x:list[float],seed:int=20261018)->list[float]:
    rng=random.Random(seed);logs=[math.log(a) for a in x];size=len(x)
    draws=[math.exp(sum(logs[rng.randrange(size)] for _ in range(size))/size) for _ in range(20000)]
    return [quantile(draws,.025),quantile(draws,.975)]
def analyze(dest:Path=DEST)->dict:
    protocol=read(dest/'protocol.json');assert protocol['independent_processes_per_point']==10
    records=[];rows=[];sources={}
    for matrix,n in POINTS:
        by_contrast={k:[] for k in ['V2/HV-A','V0/HV-A','V2/HV-B','V0/HV-B','HV-A/HV-B']};meds=[[],[],[],[]];wall_spans=[];cpu_medians=[]
        for rep in range(10):
            path=dest/'measurements'/matrix/f'N{n}'/f'run{rep}.json';x=read(path);validate(x,10,30);sources[str(path.relative_to(ROOT))]=sha(path)
            arrays=[r['samples_us'] for r in x['records']]
            for a,values in zip(meds,arrays):a.append(statistics.median(values))
            for name,ai,bi in [('V2/HV-A',1,2),('V0/HV-A',0,2),('V2/HV-B',1,3),('V0/HV-B',0,3),('HV-A/HV-B',2,3)]:
                val=statistics.median(a/b for a,b in zip(arrays[ai],arrays[bi]));by_contrast[name].append(val)
            traces=[t for t in x['trace'] if not t['warm']]
            for idx,label in enumerate(['V0','V2','HV-A','HV-B']):
                tr=[t for t in traces if t['record_index']==idx];fractions=[t['thread_cpu_ns']/(t['end_ns']-t['start_ns']) for t in tr]
                r=x['records'][idx];records.append({'matrix':matrix,'n':n,'process':rep,'label':label,'median_us':statistics.median(arrays[idx]),'mean_us':statistics.mean(arrays[idx]),'iqr_us':quantile(arrays[idx],.75)-quantile(arrays[idx],.25),'max_us':max(arrays[idx]),'thread_cpu_wall_fraction_median':statistics.median(fractions),'thread_cpu_wall_fraction_p95':quantile(fractions,.95),'cpu_migration_calls':sum(t['cpu_before']!=t['cpu_after'] for t in tr),'max_abs_error':r['max_abs_error'],'source':str(path.relative_to(ROOT))})
            for suffix in ['before','after','process']:
                p=path.with_suffix('.'+suffix+'.json');assert p.exists();sources[str(p.relative_to(ROOT))]=sha(p)
            proc=read(path.with_suffix('.process.json'));wall_spans.append((proc['end_monotonic_ns']-proc['start_monotonic_ns'])/1e9)
        null=by_contrast['HV-A/HV-B'];guard=math.exp(quantile([abs(math.log(a)) for a in null],.95))
        contrasts={}
        for name,values in by_contrast.items():
            contrasts[name]={'process_ratios':values,'geomean':gm(values),'median':statistics.median(values),'bootstrap95_conditional':interval(values),'min':min(values),'max':max(values),'faster_count':sum(a>1 for a in values),'slower_count':sum(a<1 for a in values)}
        p=contrasts['V2/HV-A'];positive=p['bootstrap95_conditional'][0]>1 and p['geomean']>guard and p['faster_count']>=8 and contrasts['V2/HV-B']['geomean']>1
        row={'matrix':matrix,'n':n,'contrasts':contrasts,'null_noise_guard':guard,'signal':'clear_positive_descriptive' if positive else 'weak_mixed_or_unresolved','process_median_max_min_by_label':{label:max(v)/min(v) for label,v in zip(['V0','V2','HV-A','HV-B'],meds)},'runner_total_wall_seconds':wall_spans}
        rows.append(row)
    result={'schema':'d0-audit-v1','passed':True,'configurations':5,'independent_processes':50,'samples_per_record':1500,'four_records_total_samples':6000,'traced_calls_including_warmup':8000,'rows':rows,'process_records':records,'source_sha256':sources,'protocol_sha256':sha(dest/'protocol.json'),'build':read(dest/'build.json'),'limits':['Trace is host-side; thread CPU is not device duration. Wall minus CPU is not a direct measure of scheduling delay.','Ten process-level blocks from one rented session; intervals are conditional exploratory bootstrap ranges, not matrix-population generalization.','Telemetry is before/after runner only; no continuous frequency/temperature/power attribution.','Two H-V records use same implementation/input but separate device allocations; index defines label.','D0 makes no algorithm/threshold changes and is not a D1 profile.']}
    for p in ['protocol.json','build.json','case_manifest.json','preflight.json','final_environment.json']:
        assert (dest/p).exists();result['source_sha256'][str((dest/p).relative_to(ROOT))]=sha(dest/p)
    save(dest/'local_audit.json',result)
    with (dest/'process_summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    lines=['# D0：五代表点计时诊断','', '50个独立进程，每点10进程，每进程10预热/30采样。四记录为V0、V2、HV-A、HV-B；两个HV相同实现/输入，独立分配。比值>1代表HV更快。','', '主计时仍为驻留输入上的同步完整调用，包含调用内B准备/清零/计算/恢复/同步，排除CPU结构准备和首次上传。主机追踪不含设备事件；原设备内核未重新编译。','', '| 点 | V2/HV-A 几何平均（条件区间） | V0/HV-A | V2/HV-B | HV-A/HV-B | 同层噪声保护值 | 主比较快/10 | 判断 |','|---|---:|---:|---:|---:|---:|---:|---|']
    for row in rows:
        c=row['contrasts'];p=c['V2/HV-A'];ci=p['bootstrap95_conditional'];lines.append(f"| {row['matrix']}/N{row['n']} | {p['geomean']:.4f} ({ci[0]:.4f}–{ci[1]:.4f}) | {c['V0/HV-A']['geomean']:.4f} | {c['V2/HV-B']['geomean']:.4f} | {c['HV-A/HV-B']['geomean']:.4f} | {row['null_noise_guard']:.4f} | {p['faster_count']} | {row['signal']} |")
    lines+=['', '“清晰正向信号”为事前描述性规则：主比较区间下端>1、几何平均超过同进程层级空对照保护值、至少8/10进程更快、HV-B聚合也>1。它不是显著性检验。未满足标为弱/混合/未分辨，不能直接说算法无效。区间按10个进程的log配对比做20000次bootstrap；没有把30迭代当作独立实验。','', '## 原始进程配对比','']
    for row in rows:
        lines += [f"### {row['matrix']}/N{row['n']}", '', '| 比较 | run0→run9 |', '|---|---|']
        for name,c in row['contrasts'].items():lines.append('| '+name+' | '+', '.join(f'{v:.5f}' for v in c['process_ratios'])+' |')
        lines += ['', '进程中位延迟max/min：'+json.dumps(row['process_median_max_min_by_label'],ensure_ascii=False), '']
    lines+=['## 解释边界','']+['- '+x for x in result['limits']]+['','逐调用主机起止/线程CPU时间、运行CPU编号与顺序在每份原始JSON的trace。进程前后设备状态和主机/proc信息另存；thread_cpu_ns的边界略宽于墙钟窗口，不当设备执行时间或精确主机开销。','', '本阶段结束后回收/备份，再关闭实例；D1没有启动。']
    (dest/'分析.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'passed':True,'points':len(rows),'processes':50,'sources':len(result['source_sha256'])}));return result
if __name__=='__main__':analyze()
