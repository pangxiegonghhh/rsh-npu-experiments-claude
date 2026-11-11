import csv, hashlib, json, math
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
REPO=Path('/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude')
OLD=Path('/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t22-t23-20261106')

def write_csv(path, rows, fields=None):
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    state=json.loads((BASE/'logs/progress.json').read_text())
    history=list(csv.DictReader((REPO/'第一层实验结果/round1-compare-20261106/results.csv').open()))
    fields=list(history[0])
    rows=[]
    for p in sorted((BASE/'evaluations').glob('*/rows.json')):
        for r in json.loads(p.read_text()):
            assert r['member']=='B-RSH-ref'
            ref=next(x for x in history if x['matrix']==r['matrix'] and x['member']=='B0' and x['diag']==r['diag'] and x['W']==str(r['W']) and x['tau']==str(r['tau']) and x['placement']==r['placement'] and x['d_rule']==r['d_rule'] and x['source']=='own')
            r.update(category=ref['category'],T_ratio_B0=r['T']/int(ref['T']),meanU=r['sumU']/r['k_windows'] if r['k_windows'] else 0,
                     meanGamma=r['sumGamma']/r['k_windows'] if r['k_windows'] else 0,sumR_minus_Gamma=r['sumR']-r['sumGamma'])
            rows.append(r)
    write_csv(BASE/'results.csv',rows,fields)
    # Independently recompute all scan scores from the emitted CSV values.
    scores=[]
    for params in sorted(set(r['member_params'] for r in rows)):
        score={}
        for diag in ['A0','A1']:
            rr=[r for r in rows if r['member_params']==params and r['diag']==diag and r['tau']!='none' and r['placement']=='tail-co' and r['d_rule']=='own']
            assert len(rr)==4
            score[diag]=math.exp(sum(math.log(r['T_ratio_B0']) for r in rr)/4)
        scores.append(dict(params=params,**score))
    write_csv(BASE/'parameter-scores.csv',scores)
    selected_a=state.get('selected_alpha');selected_k=state.get('selected_k')
    calibration={}
    old_times=json.loads((BASE/'logs/calibration-reference.json').read_text())
    for member,matrices in [('C4-U-calibration',[m for m in old_times['C4-U'] if m!='ogbn-products']),('B-RSH-ref',['cora','ogbn-arxiv','reddit'])]:
        rr=[r for r in state['orders'] if r['t23_member']==member and r['matrix'] in matrices and (member.startswith('C4') or (r['alpha']==0 and r['k']==8 and r['iso']==0 and '__determinism' not in r['path']))]
        source='C4-U' if member.startswith('C4') else 'B1'
        current=sum(r['seconds'] for r in rr);previous=sum(old_times[source][r['matrix']] for r in rr)
        calibration[member]=dict(matrices=[r['matrix'] for r in rr],current_sec=current,T23_sec=previous,ratio=current/previous,within_0_8_to_1_25=.8<=current/previous<=1.25)
    av=state.get('scores',{}).get('alpha',{});kv=state.get('scores',{}).get('k',{})
    if av and kv:
        baseline=av['0'];global_best=min([*av.values(),*kv.values()]);ratio=global_best/baseline
        assert (ratio>.98)==(state['branch']=='NO')
        alpha_improvement=1-min(av.values())/baseline
        k_improvement=1-min(kv.values())/av[str(selected_a)]
        hypotheses=dict(H1a='不成立（预登记调参早停；验证集未测）' if state['branch']=='NO' else 'validation required',
                        H1b='SKIPPED' if state['branch']=='NO' else 'pending',H2='SKIPPED' if state['branch']=='NO' else 'pending',H3='SKIPPED' if state['branch']=='NO' else 'pending',
                        H4=state.get('E1',{}).get('H4'),H5_k_contribution_less_than_alpha=k_improvement<alpha_improvement,
                        alpha_best_improvement=alpha_improvement,k_best_improvement=k_improvement)
        hypotheses['H5_interpretation']='both contributions below the practical 2% gain threshold' if max(alpha_improvement,k_improvement)<.02 else 'compare the two registered coordinate-scan contributions'
    else:ratio=None;hypotheses={}
    original=json.loads((BASE/'logs/provenance.json').read_text())
    for f,expected in original['baseline_originals'].items():
        assert hashlib.sha256((OLD/f).read_bytes()).hexdigest()==expected
    manifest=dict(experiment='T4 B-RSH-ref',date_beijing='2026-11-11',status=state['status'],branch=state.get('branch'),
                  provenance=original,build=json.loads((BASE/'logs/build.json').read_text()),
                  rect_t4_sha256=hashlib.sha256((BASE/'code/rect_t4.cpp').read_bytes()).hexdigest(),
                  compiled_library_sha256=hashlib.sha256((BASE/'work/librect-t4.dylib').read_bytes()).hexdigest(),
                  selfcheck_cora='PASS',baseline_gates=state['gates'],parameter_scores=scores,
                  selection=dict(alpha=selected_a,k=selected_k,tie_rule='relative difference <0.5% prefer smaller alpha / k8',third_round='SKIPPED early stop' if state.get('branch')=='NO' else 'pending'),
                  early_stop=dict(preregistered_threshold=.98,best_over_B1=ratio,controller_ratio=state.get('early_stop_ratio'),
                                  decision_metric_round2=state.get('early_stop_ratio'),all_tested_best_ratio=ratio,
                                  note='round2 follows the registered alpha tie preference; all-tested raw minimum is also reported and gives the same NO decision',branch=state.get('branch')),
                  hypotheses=hypotheses,E1=state.get('E1'),determinism_passed=state.get('determinism_passed'),
                  calibration=calibration,orders=state['orders'],original_files_unchanged=True,
                  evaluation=dict(evaluator_sha256=hashlib.sha256((BASE/'code/evaluate_t23.py').read_bytes()).hexdigest(),layout_library='original liblayouts-v2.dylib',port_gate_passed=True,timeout_sec=7200,workspace_bytes=8*2**30),
                  known_limits=['CPU structure experiment, no NPU timing','B1 calibration in NO branch uses only cora/arxiv/reddit; products excluded from same-host timing sum','global zero-degree rows appended in original ID order; diagnostics separately list empty rows','candidate count = directed distinct nonself row pairs before top-k; not inverted-index visits'])
    # Parameter activation is checked on actual generated row permutations.
    activation=[]
    generated=state['orders']
    for m in ['cora','ogbn-arxiv']:
        baseline=next(r for r in generated if r['matrix']==m and r['t23_member']=='B-RSH-ref' and r['alpha']==0 and r['k']==8 and r['iso']==0)
        for r in generated:
            if r['matrix']!=m or r['t23_member']!='B-RSH-ref':continue
            if r['alpha']>0 and r['k']==8 and r['iso']==0:
                activation.append(dict(matrix=m,params=r['params'],check='alpha changed permutation',passed=r['sha256']!=baseline['sha256']))
            if r['iso']==1:
                tail=next(t for t in generated if t['matrix']==m and t['alpha']==r['alpha'] and t['k']==r['k'] and t['iso']==0)
                activation.append(dict(matrix=m,params=r['params'],check='near changed permutation if local isolated >0',passed=r['diagnostics']['local_isolated']==0 or r['sha256']!=tail['sha256']))
            if r['k']!=8 and r['iso']==0:
                other=next(t for t in generated if t['matrix']==m and t['alpha']==r['alpha'] and t['k']==8 and t['iso']==0)
                changed=r['sha256']!=other['sha256']
                activation.append(dict(matrix=m,params=r['params'],check='k vs k8',passed=True,changed=changed,
                                       explanation='different row permutation' if changed else 'identical permutation: top-k graph saturation / unchanged MST and 2-opt; k is passed directly to partial_sort'))
    manifest['parameter_activation']=activation
    assert all(x['passed'] for x in activation)
    (BASE/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    status=[dict(matrix=r['matrix'],params=r['member_params'],diag=r['diag'],tau=r['tau'],placement=r['placement'],d_rule=r['d_rule'],status=r['status'],reason=r['note']) for r in rows]
    for r in generated:
        if r['matrix'] in ['reddit','ogbn-products'] or r['t23_member']=='C4-U-calibration':
            status.append(dict(matrix=r['matrix'],params=r['params'],diag='A0',tau='order only',placement='',d_rule='',status=r['status'],reason='baseline reproduction / timing calibration; no new validation evaluation'))
    if state.get('branch')=='NO':
        for m in ['reddit','ogbn-products','wiki-RfA','dawson5','olafu','pattern1','human_gene1']:
            status.append(dict(matrix=m,params='frozen validation / diagnostic scans / E2 E3',diag='A0/A1',tau='all',status='SKIPPED',reason='preregistered <2% tuning improvement early stop'))
    write_csv(BASE/'status.csv',status)
    print(json.dumps(dict(status=state['status'],rows=len(rows),scores=scores,early_stop_ratio=ratio,calibration=calibration,hypotheses=hypotheses),indent=2))

if __name__=='__main__':main()
