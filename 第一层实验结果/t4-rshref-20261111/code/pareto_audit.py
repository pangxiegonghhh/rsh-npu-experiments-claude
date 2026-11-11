"""Recompute the registered candidate pool without editing its existing shortlist."""
import csv, json, math
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
OLD=Path('/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t22-t23-20261106')
FIRST=Path('/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/第一层实验结果/round1-compare-20261106/results.csv')

def main():
    manifest=json.loads((BASE/'manifest.json').read_text());assert manifest['branch']=='NO'
    raw=list(csv.DictReader(FIRST.open()))+list(csv.DictReader((OLD/'merge-hostb-20261110/T22-T23-merged-20261110/results.csv').open()))
    matrices=[x['matrix'] for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text())]
    members=['C9-Gorder','C9-S','C10-BP','C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I','C1-J','C1-H','C5','C5-U','C8-METIS','B-RSH-ref']
    output=[]
    factor=1 if all(c['within_0_8_to_1_25'] for c in manifest['calibration'].values()) else manifest['calibration']['C4-U-calibration']['ratio']
    for diag in ['A0','A1']:
        for member in members:
            source='B1' if member=='B-RSH-ref' else member
            vals=[];cost={};categories={};fallbacks=[]
            for matrix in matrices:
                for tau in next(m['taus'] for m in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if m['matrix']==matrix):
                    def match(x,name):return x['matrix']==matrix and x['member']==name and x['diag']==diag and x['W']=='16' and x['source']=='own' and x['seed']=='0' and x['tau']==str(tau['tau']) and x['placement']=='tail-co' and x['d_rule']=='own' and bool(x['T'])
                    def pick(name):
                        found=next((x for x in raw if match(x,name)),None)
                        if found is not None:return found
                        # T23 proves T is invariant to placement and D ordering.
                        found=next(x for x in raw if x['matrix']==matrix and x['member']==name and x['diag']==diag and x['W']=='16' and x['source']=='own' and x['seed']=='0' and x['tau']==str(tau['tau']) and x['placement']=='tail' and x['d_rule']=='own' and x['T'])
                        fallbacks.append(f'{matrix}/{name}/{diag}/tau{tau["tau"]}: tail-own T invariant')
                        return found
                    r=pick(source);b=pick('B0')
                    val=int(r['T'])/int(b['T']);vals.append(val);categories.setdefault(r['category'],[]).append(val)
                    if matrix!='ogbn-products':cost[matrix]=float(r['order_sec'])
            assert len(vals)==18 and len(cost)==8
            gm=math.exp(sum(map(math.log,vals))/len(vals))
            result=dict(diag=diag,member=member,T_gm=gm,eight_matrix_seconds_inherited=sum(cost.values()),calibration_scale=factor,eight_matrix_seconds_scaled=sum(cost.values())*factor,T_invariant_fallbacks='; '.join(fallbacks))
            for c,values in categories.items():
                g=math.exp(sum(map(math.log,values))/len(values));result[c+'_gm']=g;result[c+'_worst']=max(values);result[c+'_effective']=g<=.95 and max(values)<=1.05
            output.append(result)
        pool=[r for r in output if r['diag']==diag]
        for r in pool:r['pareto']=not any(s['T_gm']<=r['T_gm'] and s['eight_matrix_seconds_scaled']<=r['eight_matrix_seconds_scaled'] and (s['T_gm']<r['T_gm'] or s['eight_matrix_seconds_scaled']<r['eight_matrix_seconds_scaled']) for s in pool)
    fields=list(dict.fromkeys(k for r in output for k in r))
    with (BASE/'pareto-audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(output)
    (BASE/'pareto-audit-note.md').write_text('候选池按 T23 的14个候选加 B-RSH-ref 重新计算。NO分支的 B-RSH-ref 使用冻结B1成绩，未伪造七张验证集实测；时间均明确为继承的同主机八张之和。校准触发时统一按C4-U比例折算。A0/A1、类别有效性和非支配标记见CSV。\n\n至多3个名额同时要求类别覆盖，原规则未提供冲突时的确定性取舍算法；此表提供复审依据，不改已有短名单或 candidates.md，也不把规划方的最终取舍冒充执行事实。\n')
    print({d:[r['member'] for r in output if r['diag']==d and r['pareto']] for d in ['A0','A1']})

if __name__=='__main__':main()
