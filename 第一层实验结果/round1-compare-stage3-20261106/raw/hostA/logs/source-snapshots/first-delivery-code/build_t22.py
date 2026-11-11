import csv,json,shutil,time
from pathlib import Path
from artifact_pack import BASE,sha,dump,source_proof,install_orders,install_sources,copy_file,environment,seal
from collect_t22 import collect
from collect_t23_first import dumpcsv

def build():
 collect();col=BASE/'work/t22-collected';cov=json.loads((col/'coverage.json').read_text());assert cov['OK']==170 and cov['result_rows']==4012 and cov['pls_records']==182,cov
 derived={n:json.loads((BASE/'work/t22-derived'/(n+'.json')).read_text()) for n in ['four_numbers','kendall','cross_tau']}
 assert len(derived['four_numbers'])==340 and len(derived['kendall'])==168 and len(derived['cross_tau'])==112
 assert all(r['status']=='OK' for n in ['kendall','cross_tau'] for r in derived[n])
 assert all(isinstance(r.get('T_rerun'),(int,float)) or r['member'].startswith('LS-full') for r in derived['four_numbers'])
 name='rq3-validate-20261106';dest=BASE/'delivery/第一层实验结果'/name;assert not dest.exists();root=BASE/'work/staging'/f'{name}-{time.time_ns()}';root.mkdir(parents=True);proof=source_proof()
 for n in ['results.csv','pls.csv','status.csv','guard-counts.csv','coverage.json']:copy_file(col/n,root/n)
 for n,rows in derived.items():dumpcsv(root/(n+'.csv'),rows)
 orders=json.loads((col/'new-orders.json').read_text());info=install_orders(root,name,orders);codes=install_sources(root)
 reuse=[r for r in json.loads((BASE/'logs/reused-orders.json').read_text()) if r['task']=='T22' or r['task']=='T23' and r['use']=='W-sensitivity' and r['matrix'] in ['cora','ogbn-arxiv'] and int(r['W']) in [32,64]]
 meta=[r for r in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if r['matrix'] not in ['reddit','ogbn-products']]
 logs=root/'logs';logs.mkdir()
 for p in (BASE/'logs').iterdir():
  if p.is_file() and p.name.startswith(('t21-reference','t22-','reference-','rq3-','layout-','ls-','rect-','reused-','input-reuse','independent-','matrices-and-taus','first-batch','repository-before','request-source','resource-policy','host-resource','member-label','empty-seed','seed-bug','cpu-queue','global-cpu','software-versions','cpu-compiler')):copy_file(p,logs/p.name)
 for folder in ['source-snapshots','queue-probe-failure','workflow-before-queue-fix','cpu-slot-starts']:
  if (BASE/'logs'/folder).exists():shutil.copytree(BASE/'logs'/folder,logs/folder)
 for folder in ['t22-evaluations','t22-new-evaluations','t22-layout-repairs','order-jobs','extra-order-jobs']:
  for p in (BASE/'work'/folder).rglob('*.json'):
   if p.name.endswith('order.json') or 'checkpoint' in p.name:continue
   copy_file(p,logs/'raw'/folder/p.relative_to(BASE/'work'/folder))
 manifest=dict(experiment='T22 RQ3 validation',repository=proof,CPU_only=True,NPU_used=False,environment=environment(),matrices=meta,coverage=cov,reused_orders=reuse,new_orders=info,code_and_runtime=codes,parameters=dict(W_main=16,W_sensitivity=[32,64],LS_lambda=[0,1],LS_max_sweeps=10,seed=0,co_chain_skip_threshold=400,method_timeout_seconds=7200),metadata_normalization='authoritative labels reconstructed from source records; Unix start timestamp is not a member label; original numeric outputs unchanged',reuse_note='97 indexed T22 orders plus16 verified T23 W32/W64 orders; retained frozen order vectors including historical SlashBurn/empty-node behavior',timing_note='raw per-case wall times and original T21 costs retained; CPU queue delays recorded; no timing fabricated',results_source='original successful records plus14 packed-v2 gap supplement rows; failed original attempts retained',analysis_conclusions_written=False,git_commit_or_push_performed=False)
 dump(root/'manifest.json',manifest)
 states=list(csv.DictReader(open(root/'status.csv')));guards=list(csv.DictReader(open(root/'guard-counts.csv')))
 lines=['# T22 RQ3 验证实验','',f'CPU实验；提交 {proof["commit"]}，树 {proof["tree"]}；原有{proof["verified_original_files"]}个文件哈希未变。未提交、未推送。','',f'170个条件单元、4012行结果、182条P-LS记录；四数表340行、Kendall168行、跨τ112行。逐项状态见status.csv。复用{len(reuse)}条行序引用；新生成{info["file_count"]}个文件，共{info["total_bytes"]}字节。超过50MiB的新行序按派发仅留本地，路径和SHA见orders-manifest.json。','', 'M1的inplace保留原窗口再删除残余成员；M5的inplace是在保留编号位置放置残余，因此其T等于keep。两者按方案分别记录。','', '原始seed空字符串错误数据已隔离，队列启动失败、原版gap内存守卫失败均保留。只补齐未成功条件；gap使用经过逐项等值自检的打包端口表示。方法标签从原始来源记录规范化，未重算数值。','', 'co_chain单窗口涉及残余点>400时跳过该窗口co计数，规则保持。完整逐条件计数见guard-counts.csv。','', 'T21/T22参考复现、移植等值、独立复核、复用P-LS不变量检查见logs。未写分析结论。','', '## τ和显式零','', '|matrix|τ|显式零条目|','|---|---|---|']
 for m in meta:lines.append('|'+m['matrix']+'|'+', '.join(t['tau_rule']+'='+str(t['tau']) for t in m['taus'])+'|'+str(m['explicit_zero_entries'])+'|')
 lines+=['','## co_chain守卫','','累计值为条件计数求和，不代表去重窗口数。','','|matrix|tau|有计数条件数|单条件最小|单条件最大|累计|','|---|---|---|---|---|---|']
 for m in meta:
  for t in m['taus']:
   values=[int(g['co_chain_guard_windows_skipped']) for g in guards if g.get('matrix')==m['matrix'] and str(g.get('tau'))==str(t['tau']) and g.get('co_chain_guard_windows_skipped','')!=''];lines.append(f'|{m["matrix"]}|{t["tau"]}|{len(values)}|{min(values) if values else "NA"}|{max(values) if values else "NA"}|{sum(values)}|')
 lines+=['','## 矩阵 × 方法状态','','|matrix|member|W|tau|status|reason|','|---|---|---|---|---|---|']+[f'|{r["matrix"]}|{r["member"]}|{r["W"]}|{r["tau"]}|{r["status"]}|{r["reason"]}|' for r in states];(root/'README.md').write_text('\n'.join(lines)+'\n');dest.parent.mkdir(parents=True,exist_ok=True);root.rename(dest);receipt=seal(dest,name);dump(BASE/'delivery'/(name+'.receipt.json'),receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':build()
