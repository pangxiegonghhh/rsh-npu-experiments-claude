import csv,datetime,json,shutil,time
from pathlib import Path
from artifact_pack import BASE,sha,dump,source_proof,install_orders,install_sources,copy_file,environment,seal
from collect_stage3 import collect
from audit_results import audit
from collect_t23_first import dumpcsv
from first_group_supplement import rows as first_group_rows
from source_provenance_audit import audit as source_audit

def build():
 cov=collect();assert cov['all_attempted'],cov;source_versions=source_audit();assert source_versions['passed'],'missing actual imported source version';col=BASE/'work/stage3-collected';start=json.loads((BASE/'logs/stage3-start.json').read_text())['start'];date=datetime.datetime.fromtimestamp(start,datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%d');name='round1-compare-stage3-'+date;final=BASE/'delivery/第一层实验结果'/name;assert not final.exists();root=BASE/'work/staging'/f'{name}-{time.time_ns()}';root.mkdir(parents=True);proof=source_proof();validation=audit(col/'results.csv');dump(root/'independent-table-audit.json',validation)
 for n in ['results.csv','diag.csv','groups.csv','status.csv','guard-counts.csv','post-E.csv','coverage.json']:copy_file(col/n,root/n)
 inherited=[]
 for r in json.loads((BASE/'logs/reused-pls-invariants.json').read_text())['checks']:
  if r['member'] in ['C9-Gorder','rsh-α0'] and r['lam']==0:inherited.append(dict(matrix=r['matrix'],member='B1' if r['member']=='rsh-α0' else r['member'],W=16,tau=r['tau'],seed=0,first_delivery_reuse_execution_post_sec=0,inherited_T21_post_computation_seconds=r['T21_order_sec'],source_path=r['source_path'],source_sha256=r['source_sha256'],fresh_UG_verified=True))
 assert len(inherited)==12;dumpcsv(root/'first-delivery-reused-post-costs.csv',inherited)
 dumpcsv(root/'first-delivery-group-diagnostics.csv',first_group_rows())
 orderinfo=install_orders(root,name,json.loads((col/'new-orders.json').read_text()));reused=json.loads((col/'reused-orders.json').read_text());codes=install_sources(root);copy_file(BASE/'deps/kahypar-km1-kway-v1.3.7.ini',root/'code/config/kahypar-km1-kway-v1.3.7.ini');codes.append(dict(path='code/config/kahypar-km1-kway-v1.3.7.ini',sha256=sha(root/'code/config/kahypar-km1-kway-v1.3.7.ini')));meta=json.loads((BASE/'logs/matrices-and-taus.json').read_text());independent=[]
 for m in ['reddit','ogbn-products']:
  p=BASE/'work/stage3-independent'/m/'status.json';assert p.exists(),'independent3-order attempt required before delivery';independent.append(json.loads(p.read_text()))
 assert all(r['status']=='OK' and r.get('independent_orders',0)>=3 for r in independent),'required second-batch independent3-order gates must pass before reporting numbers'
 logs=root/'logs';logs.mkdir()
 for p in (BASE/'logs').iterdir():
  if p.is_file() and p.name.startswith(('stage3-','shared-','hp-','partial-','memory-','group-','c1-','adaptive-','kahypar-','rabbit-','linux-second-','independent-','t21-reference','t22-reference','t23-reference','reference-','candidate-port','layout-port','rect-port','capacity-','cpu-queue','software-versions','cpu-compiler','reused-orders','matrices-and-taus','request-source','repository-before','second-','reddit','products','mycielskian')):copy_file(p,logs/p.name)
 if (BASE/'logs/memory-guards').exists():shutil.copytree(BASE/'logs/memory-guards',logs/'memory-guards')
 if (BASE/'logs/source-snapshots').exists():shutil.copytree(BASE/'logs/source-snapshots',logs/'source-snapshots')
 for folder in ['stage3-generated','external','generated']:
  for pattern in ['*.phase.json','*.cost-budget*.json','*.pre-repair-labels.npy']:
   for p in (BASE/'work'/folder).glob(pattern):copy_file(p,logs/'generation-checkpoints'/folder/p.name)
 for folder in ['stage3-cases','stage3-evaluations','stage3-diagnostics','stage3-independent','stage3-partial-post']:
  for p in (BASE/'work'/folder).rglob('*.json'):
   if p.name.endswith('order.json') or 'checkpoint' in p.name:continue
   copy_file(p,logs/'raw'/folder/p.relative_to(BASE/'work'/folder))
 for p in (BASE/'work/post-e').glob('stage3-*/*.json'):
  if p.name in ['record.json','rows.json']:copy_file(p,logs/'raw/post-e'/p.relative_to(BASE/'work/post-e'))
 for p in (BASE/'work/rabbit-coarse').glob('*'):
  if p.is_file() and p.name.startswith(('reddit-','ogbn-products-')):copy_file(p,logs/'rabbit-coarse'/p.name)
 manifest=dict(experiment='T23 stage3 P1/P2 W sensitivity second batch',repository=proof,first_delivery_receipt=json.loads((BASE/'delivery/round1-compare-20261106.receipt.json').read_text()),environment=environment(),matrices=meta,coverage=cov,planned_cases=json.loads((BASE/'logs/stage3-planned-cases.json').read_text()),new_orders=orderinfo,reused_orders=reused,code_and_runtime=codes,independent_second_batch=independent,parameters=dict(W=[16,32,64,128],W_sensitivity_matrices=['cora','ogbn-arxiv','wiki-RfA','dawson5'],W_sensitivity_taus='full and main tau only',LS_sweeps_max=10,seed0=True,actual_method_timeout_sec=7200,queue_delay_excluded=True,workspace_budget_bytes=8*2**30,co_chain_guard=400),C3_A_alias='b=4 below50000 equalsC3-W4, explicitly nonindependent alias; -R b4 likewise marked',C6_T21_scope='28 frozen first-batch RB/M orders epsilon0; no recomputation. Second-batch frozen RB/M absent, SKIPPED rather than re-label epsilon.03 new outputs asT21',Rabbit_seed_note='author has no seed API/RNG; requested replica1/2 labels correspond actual serial deterministic repeated coarse runs, actual seed null',timing_note='new method wall includes cached CSR mmap setup; layout generation and metric time in d_sec; original raw total-case/queue times preserved',analysis_conclusions_written=False,git_commit_or_push_performed=False)
 dump(root/'manifest.json',manifest);states=list(csv.DictReader(open(root/'status.csv')));guards=list(csv.DictReader(open(root/'guard-counts.csv')))
 manifest['timing_clarifications']=dict(first_reused_post_E='first delivery post_sec0 is actual current-run reuse execution cost; original T21 computation costs supplied separately in first-delivery-reused-post-costs.csv; no first-delivery files modified',Rabbit='record.seconds=coarse_seconds+local_seconds. CSR mmap-object/coarse-map loading and serialization outside local timer are available in raw start/end elapsed; generic cached-CSR timing note in first delivery does not apply to those Rabbit phases',C1='raw order wall includes approximate graph, exact forest and128-row recall diagnostic; diagnostic cost was not invented or subtracted from historical records');manifest['group_diagnostic_normalization']='C3-W4-noP unfilled raw diagnostic fields reconstructed from saved actual generation group sizes; grouping metadata for70first-primary entries supplied in first-delivery-group-diagnostics.csv. No order/UT/R changes or rewrites of first delivery; see logs/group-diagnostic-metadata-normalization.json';dump(root/'manifest.json',manifest)
 lines=['# T23 第三阶段','',f'基准提交 {proof["commit"]}，原有{proof["verified_original_files"]}个文件哈希不变；纯CPU，不提交、不推送。','',f'计划{cov["planned_cases"]}例，已尝试{cov["attempted"]}例：OK {cov["OK"]}，INCOMPLETE {cov["INCOMPLETE"]}，SKIPPED {cov["SKIPPED"]}。状态与原因逐项见status.csv。超时、内存门限或依赖失败如实留证。','',f'本次复用引用{len(reused)}条，新行序文件{orderinfo["file_count"]}个、合计{orderinfo["total_bytes"]} B；超过50MiB仅留本地，逐文件大小和SHA见orders-manifest.json。','', 'C6-RB/M按T21口径复用，不与新C6-HP混为同一划分器配置。C3-A在b=4时为非独立别名；Rabbit无种子接口，重复编号不冒充随机种子。','', 'mycielskian15官方数据获取失败，保留SKIPPED。第二批实际条目数以manifest为准，不为匹配文献表改图。wiki-RfA保留指定重建输入和显式零，B0/P11只作参考。','', '第一批目录已封存，本次单独交回。未写分析结论。','', '## τ与显式零','','|matrix|τ规则和值|显式零条目|','|---|---|---|']
 for m in meta:lines.append('|'+m['matrix']+'|'+', '.join(t['tau_rule']+'='+str(t['tau']) for t in m['taus'])+'|'+str(m['explicit_zero_entries'])+'|')
 lines+=['','首包复用P-LS的post_sec=0记录本轮直接复用的计算开销；12条输出在T21中的原始计算耗时另列于first-delivery-reused-post-costs.csv。Rabbit的算法耗时为coarse_seconds+local_seconds，读入粗序与序列化等开销另见原始start/end；C1原始总耗时含128行召回率诊断。首包未改写。','','C3-W4-noP原始导出未填的分组计数按已保存的实际组大小补正；首包成组候选的70条补充诊断见first-delivery-group-diagnostics.csv。原始记录保留，行序及U/T/R数值未变。','','## co_chain守卫','','单窗口涉及残余点>400时跳过co计数，逐条件见guard-counts.csv；累计按条件相加，未去重。','','|matrix|tau|条件数|最小|最大|累计|','|---|---|---|---|---|---|']
 for m in meta:
  for t in m['taus']:
   values=[int(g['co_chain_guard_windows_skipped']) for g in guards if g.get('matrix')==m['matrix'] and str(g.get('tau'))==str(t['tau']) and g.get('co_chain_guard_windows_skipped','')!=''];lines.append(f'|{m["matrix"]}|{t["tau"]}|{len(values)}|{min(values) if values else "NA"}|{max(values) if values else "NA"}|{sum(values)}|')
 lines+=['','## 矩阵 × 方法状态','','|matrix|member|W|seed|status|reason|','|---|---|---|---|---|---|']+[f'|{r["matrix"]}|{r["member"]}|{r["W"]}|{r["seed"]}|{r["status"]}|{r["reason"]}|' for r in states];(root/'README.md').write_text('\n'.join(lines)+'\n');final.parent.mkdir(parents=True,exist_ok=True);root.rename(final);receipt=seal(final,name);dump(BASE/'delivery'/(name+'.receipt.json'),receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':build()
