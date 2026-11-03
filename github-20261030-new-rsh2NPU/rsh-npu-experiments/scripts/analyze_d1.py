"""Offline D1 process-level paired statistics and diagnostic cost tables."""
from __future__ import annotations
import csv,json,math,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import POINTS,LABELS,sha,read,save
from scripts.run_d1 import validate
from scripts.analyze_d0 import gm,interval,quantile
D=ROOT/'results/d1'
CONTRASTS=[('V2/V2-Z',1,2),('V2-Z/HV-A',2,3),('V2/HV-A',1,3),('V0/HV-A',0,3),('V2/HV-B',1,4),('V2-Z/HV-B',2,4),('HV-A/HV-B',3,4)]
def main():
    rows=[];process=[];event_table=[];sources={}
    for m,n in POINTS:
        ratios={name:[] for name,_,_ in CONTRASTS};medians={l:[] for l in LABELS};errors=[]
        for rep in range(10):
            p=D/'measurements'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30);sources[str(p.relative_to(ROOT))]=sha(p)
            a=[r['samples_us'] for r in x['records']]
            for i,l in enumerate(LABELS):
                medians[l].append(statistics.median(a[i]));process.append({'matrix':m,'n':n,'rep':rep,'label':l,'median_us':statistics.median(a[i]),'valid_rows':x['records'][i]['valid_rows'],'m':x['records'][i]['m'],'max_abs_error':x['records'][i]['max_abs_error']})
            for name,i,j in CONTRASTS:ratios[name].append(statistics.median(u/v for u,v in zip(a[i],a[j])))
            errors.extend(r['max_abs_error'] for r in x['records'])
            for suffix in ['before','after','process']:
                q=p.with_suffix('.'+suffix+'.json');sources[str(q.relative_to(ROOT))]=sha(q)
        guard=math.exp(quantile([abs(math.log(v)) for v in ratios['HV-A/HV-B']],.95));cs={}
        for name,_,_ in CONTRASTS:
            vals=ratios[name];ci=interval(vals);mean=gm(vals);count=sum(v>1 for v in vals)
            confirm=gm(ratios[name.replace('HV-A','HV-B')])>1 if 'HV-A' in name and name.replace('HV-A','HV-B') in ratios else True
            cs[name]={'process_ratios':vals,'geomean':mean,'bootstrap95_conditional':ci,'faster_count':count,'clear_positive_descriptive':ci[0]>1 and mean>guard and count>=8 and confirm}
        event_by_label=[]
        for i,l in enumerate(LABELS):
            values=[];walls=[];fractions=[]
            for rep in range(3):
                p=D/'profile'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30,True);sources[str(p.relative_to(ROOT))]=sha(p)
                ev=x['events'][i];v=[statistics.median(z[j] for z in ev) for j in range(5)];values.append(v);walls.append(statistics.median(x['records'][i]['samples_us']));fractions.append(statistics.median(z[-1]/w for z,w in zip(ev,x['records'][i]['samples_us'])))
            e={'label':l,'fields_us':['out_clear','packed_clear','main_with_B_gather','restore','device_span'],'process_component_medians_us':values,'component_median_of_processes_us':[statistics.median(v[j] for v in values) for j in range(5)],'profile_wall_process_medians_us':walls,'profile_wall_median_us':statistics.median(walls),'span_wall_fraction_process_medians':fractions,'empty_valid_scope':next(p for p in process if p['matrix']==m and p['n']==n and p['label']==l)['valid_rows']==0}
            event_by_label.append(e);event_table.append({'matrix':m,'n':n,'label':l,**dict(zip(e['fields_us'],e['component_median_of_processes_us'])),'profile_wall_us':e['profile_wall_median_us']})
        rows.append({'matrix':m,'n':n,'contrasts':cs,'null_guard':guard,'formal_process_medians_us':medians,'events':event_by_label,'max_abs_error':max(errors)})
    out={'schema':'d1-analysis-v1','passed':True,'formal_processes':50,'event_processes':15,'formal_samples':10500,'event_samples':3150,'formal_trace_calls':14000,'event_trace_calls':4200,'rows':rows,'process_records':process,'source_sha256':sources,'limits':['Five selected points, one rented session. Ten process blocks are independent launches, not independent hardware/matrix samples. Bootstrap ranges are exploratory conditional intervals.','Formal speed ratios use original D0 host trace executable with no device events. Profile timings are separate and perturb execution.','Event main includes B gather/data transforms/MMAD or AIV work. Event gaps include stream/launch effects, not pure compute. Device span/wall residual is not a direct CPU overhead estimate.','G-only/ST-only validate only their frozen owned rows; empty scope is not numerical coverage evidence. No full SpMM claim or overlap inference from sum/max.','V2-Z deletes whole zero-K groups; it also shifts surviving group task indices/static core assignment. Not a kernel-only restore cost estimate. No nonempty group member/block changes.','No D2 threshold change, D3 joint-grouping experiment or strong sparse-library baseline in this stage.']}
    save(D/'local_audit.json',out)
    for name,data in [('process_summary',process),('event_summary',event_table)]:
        with (D/(name+'.csv')).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    lines=['# D1 实验结果','','五个代表点，各10个独立进程正式对照、3个独立进程事件诊断；每进程10预热/30采样。正式加速比只使用未插设备事件的完整同步调用。','','| 点 | V2/V2-Z | V2-Z/HV-A | V2/HV-A | V0/HV-A | HV空对照 | 噪声保护值 |','|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        c=r['contrasts'];lines.append('| '+r['matrix']+'/N'+str(r['n'])+' | '+' | '.join(f"{c[k]['geomean']:.4f}" for k in ['V2/V2-Z','V2-Z/HV-A','V2/HV-A','V0/HV-A','HV-A/HV-B'])+f" | {r['null_guard']:.4f} |")
    lines+=['','比值>1表示分母更快。每进程先取30个迭代配对比中位数，再对10进程做几何平均；条件区间由20000次进程bootstrap得到。描述性清晰信号要求下界>1、均值超过空对照保护值、至少8/10同向，HV-B确认方向。全部原始样本与进程配对比保留。','','## 设备分项诊断','','各分项分别取采样中位数，再取三进程中位数；因此分项中位数不要求严格相加等于总中位数。原始每次事件分项和总span的可加性单独检查。单位μs。','','| 点 / 标签 | 输出清零 | packed清零 | 主核含B收集 | 恢复 | 设备span | 插桩完整墙钟 |','|---|---:|---:|---:|---:|---:|---:|']
    for r in event_table:lines.append('| '+r['matrix']+'/N'+str(r['n'])+' '+r['label']+' | '+' | '.join(f'{r[k]:.3f}' for k in ['out_clear','packed_clear','main_with_B_gather','restore','device_span','profile_wall_us'])+' |')
    lines+=['','## 各点条件区间与方向','']
    for r in rows:
        lines += [f"### {r['matrix']} / N{r['n']}",'']
        for k,c in r['contrasts'].items():
            ci=c['bootstrap95_conditional'];lines.append(f"- {k}：{c['geomean']:.6f}，条件区间[{ci[0]:.6f}, {ci[1]:.6f}]，{c['faster_count']}/10同向；清晰描述性正信号={c['clear_positive_descriptive']}。进程比："+', '.join(f'{v:.6f}' for v in c['process_ratios']))
        lines.append('')
    lines+=['## 解释边界','']+['- '+s for s in out['limits']]
    (D/'分析.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'passed':True,'formal':50,'event':15,'max_abs_error':max(r['max_abs_error'] for r in rows)}))
if __name__=='__main__':main()
