import csv,hashlib,json,shutil,time
import numpy as np
from naming import t23_name
from pathlib import Path
from artifact_pack import BASE,sha,dump,source_proof,install_orders,install_sources,copy_file,environment,seal
from collect_t23_first import collect,dumpcsv,MATRICES,PRIMARY,P0
from audit_results import audit
def build():
 collect();collected=BASE/'work/t23-first-collected';coverage=json.loads((collected/'coverage.json').read_text());assert coverage['complete'],coverage;validation=audit(collected/'results.csv');name='round1-compare-20261106';finalroot=BASE/'delivery/第一层实验结果'/name;assert not finalroot.exists(),'delivery directory already exists; preserve it';root=BASE/'work/staging'/f'{name}-{time.time_ns()}';root.mkdir(parents=True);proof=source_proof();dump(root/'independent-table-audit.json',validation)
 for n in ['results.csv','diag.csv','groups.csv','post-E.csv','coverage.json','verified-T21-postE-reuse.json']:copy_file(collected/n,root/n)
 new=json.loads((collected/'new-orders.json').read_text());orderinfo=install_orders(root,name,new);codes=install_sources(root);meta=[x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if x['matrix'] in MATRICES];reuse=[x for x in json.loads((BASE/'logs/reused-orders.json').read_text()) if x['task']=='T23' and (x['use']=='post-E-reuse' or x['use']=='base-order' and not x['t23_member'].startswith('C6'))]
 guards=[]
 for p in (BASE/'work/t23-evaluations').glob('*/guards.json'):
  if (p.parent/'status.json').exists():
   first=json.loads((p.parent/'rows.json').read_text())[0]
   for r in json.loads(p.read_text()):r.update(seed=int(first.get('seed') or 0),member=t23_name(r['member']),diag='A'+str(r['diag']) if isinstance(r['diag'],int) else r['diag']);guards.append(r)
 for p in (BASE/'work/post-e').glob('*/rows.json'):
  record=p.parent/'record.json'
  if not record.exists():continue
  r=json.loads(record.read_text());member=r.get('member',r.get('method',''))
  if member.startswith(('rabbit-pilot','neutron-pilot')):continue
  for row in json.loads(p.read_text()):
   if 'co_chain_guard_windows_skipped' in row:
    g={k:row.get(k) for k in ['matrix','member','W','tau','diag','source','placement','d_rule','seed','co_chain_guard_windows_skipped']};g['member']=t23_name(g['member']);guards.append(g)
 dumpcsv(root/'guard-counts.csv',guards);state=[];results=list(csv.DictReader(open(root/'results.csv')))
 for matrix in MATRICES:
  for member in PRIMARY:
   rows=[r for r in results if r['matrix']==matrix and r['member']==member];bad=[r['note'] for r in rows if r['status']!='OK'];state.append(dict(matrix=matrix,member=member,status='INCOMPLETE' if bad else 'OK',result_rows=len(rows),reason='; '.join(sorted(set(bad)))))
  for member in ['B-RSH-ref','B-Neutron-ref']:state.append(dict(matrix=matrix,member=member,status='SKIPPED',result_rows=0,reason='T4/T2 reference dependency not available; optional by plan'))
 dumpcsv(root/'status.csv',state);logroot=root/'logs';logroot.mkdir();prefixes=('t21-reference','t22-reference','t23-','reference-','candidate-','layout-','rq3-native-','ls-port-','capacity-','independent-','external-','c1-','metis-','rabbit-','post-e-','bp-variance','pip-','build-','queue-','global-cpu-','cpu-queue-','input-reuse','matrix-preparation','reused-orders','matrices-and-taus','first-batch-matrices','repository-before','request-source','resource-policy','host-resource','member-label')
 for p in (BASE/'logs').iterdir():
  if p.is_file() and p.name.startswith(prefixes+('software-versions','cpu-compiler','kahypar-runtime','reused-pls','local-vm','linux-console','qemu-version','linux-boot')):copy_file(p,logroot/p.name)
 for dirname in ['queue-probe-failure','workflow-before-queue-fix','source-snapshots','cpu-slot-starts','rabbit-linux-build-evidence']:
  src=BASE/'logs'/dirname
  if src.exists():shutil.copytree(src,logroot/dirname)
 for source,dest,allowed in [('independent-all','independent-all',{'.stdout','.stderr','.json'}),('t23-evaluations','raw-evaluations',{'.json'}),('t23-diagnostics','raw-diagnostics',{'.json'}),('post-e','raw-post-e',{'.json'}),('rabbit-coarse','rabbit-coarse',{'.mapping','.stderr','.json'})]:
  for p in (BASE/'work'/source).rglob('*'):
   if not p.is_file() or p.suffix not in allowed:continue
   if p.name.endswith('order.json') or 'checkpoint' in p.name or p.name.endswith('-input.json'):continue
   if source=='post-e' and p.name not in ['record.json','rows.json']:continue
   copy_file(p,logroot/dest/p.relative_to(BASE/'work'/source))
 for m in meta:
  degree=np.load(BASE/'work/matrices'/m['matrix']/'degrees.npy');m['active_residual_masks']={str(t['tau']):dict(count=int(np.count_nonzero(degree<=t['tau'])),sha256=hashlib.sha256(json.dumps(np.flatnonzero(degree<=t['tau']).tolist(),separators=(',',':')).encode()).hexdigest(),serialization='sorted original IDs as compact JSON array',same_mask_A0_A1=True) for t in m['taus']}
 manifest=dict(experiment='T23 first delivery: stages1-2',run_date_beijing='2026-11-06',repository=proof,CPU_only=True,NPU_used=False,environment=environment(),matrices=meta,reused_orders=reuse,new_orders=orderinfo,code_and_runtime=codes,coverage=coverage,global_parameters=dict(W=16,K0=16,primary_seed=0,variance_seeds=[1,2],variance_matrices=['cora','ogbn-arxiv'],LS_sweeps_max=10,LS_lambda=0,co_chain_guard_skip_if_residual_points_in_window_gt=400,timeout_seconds=7200,workspace_budget_bytes=8*2**30),T_ratio_B0='same matrix/diag/W/tau/placement/d_rule; denominator B0 source=own, seed0',B0_postE='additional baseline control, source post-E; historical pilot post-E traces retained as diagnostics only',reuse_overrides='frozen T21 indexed orders retained verbatim, including their original handling of empty vertices; newly computed pure/tool candidates append empty A0 vertices in original-ID order',Rabbit_seed_note='author demo has no seed API or RNG; serial OMP1 requested replicas1/2 are actual repeat executions; actual seed null, not alternate RNG draws',timing_note='new method records include cached CSR mmap-object setup; d_sec is layout generation plus metrics from shared preconstructed incidence contexts, whose setup is included in raw total-case wall time; original timing records and queue delays retained; reused T21 order costs inherited, reused P-LS post_sec0',data_constraints='stored entries including explicit zeros; A0 symmetric union with diagonal removed; A1 adds full diagonal only for evaluation; residual masks from A0 for both',analysis_conclusions_written=False,git_commit_or_push_performed=False)
 dump(root/'manifest.json',manifest)
 lines=[f'# T23 阶段1–2：{name}','',f'CPU 结构实验；基准提交 {proof["commit"]}，树 {proof["tree"]}。仓库原有 {proof["verified_original_files"]} 个文件哈希均未变，未提交、未推送。','',f'已覆盖 {coverage["expected_own_cases"]} 个 W16 行序评估例（主种子与波动例），{coverage["expected_post_cases"]} 个后处理例。逐项状态见 status.csv；各 τ 实算值与原始输入来源、显式零数见 manifest.json。','',f'复用行序引用 {len(reuse)} 个；新行序文件 {orderinfo["file_count"]} 个、合计 {orderinfo["total_bytes"]} B。新行序超过50 MiB时按派发仅留本地，逐文件路径与SHA-256见 orders-manifest.json。','', 'T21、T22、T23参考自检、八个官方行序SHA、40行评价网格、外部工具同种子重复及每张矩阵三行序独立核对均见 logs。','', 'Rabbit 使用原作者锁定提交、Linux ARM、Boost1.58、gperftools2.16、单线程。作者无种子接口，1/2标记为确定性重复，不伪装成不同随机种子。PyNNDescent、METIS环境与编译选项见 manifest.json 和日志。','', 'co_chain 守卫：窗口涉及残余点超过400时跳过该窗口的co计数。guard-counts.csv逐条件列出实际触发窗口数；不同成员、窗口宽度与来源分别记账。','', '时序与故障：空字符串种子错误的T22临时数据已隔离；队列存活探测的启动错误已保存并补齐未启动项。T23已复用T21的P-LS输出，其重复验证副本不计入主新行序。日志保留原始证据。','', 'RSH和rabbit/neutron先导版按原名称/基线记账；历史先导参照不参加排名。B-RCM-ref只供带状矩阵排名。wiki-RfA为指定重建版，B0和P11的ΣR/ΣU只作参考。','', '未写研究分析结论。阶段3单独交回，不修改本目录。','', '## τ 与显式零值','', '|matrix|τ规则和值|显式零条目|','|---|---|---|']
 for m in meta:lines.append('|'+m['matrix']+'|'+', '.join(t['tau_rule']+'='+str(t['tau']) for t in m['taus'])+'|'+str(m['explicit_zero_entries'])+'|')
 lines+=['','## co_chain守卫触发','','每个条件的计数见 guard-counts.csv。下表仅汇总tail-co调用；累计值按条件相加，未对窗口去重。','','|matrix|tau|条件数|单条件最小|单条件最大|累计跳过窗口数|','|---|---|---|---|---|---|']
 for m in meta:
  for t in m['taus']:
   values=[int(g['co_chain_guard_windows_skipped']) for g in guards if g['matrix']==m['matrix'] and str(g['tau'])==str(t['tau']) and g['placement']=='tail-co'];lines.append(f'|{m["matrix"]}|{t["tau"]}|{len(values)}|{min(values) if values else "NA"}|{max(values) if values else "NA"}|{sum(values)}|')
 lines+=['','## 矩阵 × 方法状态','','|matrix|member|status|reason|','|---|---|---|---|']+[f'|{r["matrix"]}|{r["member"]}|{r["status"]}|{r["reason"]}|' for r in state];(root/'README.md').write_text('\n'.join(lines)+'\n');finalroot.parent.mkdir(parents=True,exist_ok=True);root.rename(finalroot);receipt=seal(finalroot,name);dump(BASE/'delivery'/f'{name}.receipt.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':build()
