"""Formally seal terminal T23 evidence and prepare a binary-free transfer.

No scientific method is invoked. Existing sealed results are immutable inputs.
Missing timing components stay missing; cumulative timers are never differenced.
"""
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

BASE=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
MERGE=BASE/'merge-hostb-20261110/T22-T23-merged-20261110'
VIEW=BASE/'merge-hostb-20261110/view'
REMOTE=BASE/'remote-evidence/hostB-windows16gb-wsl2/t23-hostb-results'
DATE=dt.datetime.fromtimestamp(json.loads((BASE/'logs/stage3-start.json').read_text())['start'],ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d')
NAME='round1-compare-stage3-'+DATE
ROOT=BASE/'delivery/第一层实验结果'/NAME
MISSING='缺失'
csv.field_size_limit(32*2**20)

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def dump(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def copy(p,q):
    q=Path(q);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);assert sha(p)==sha(q)
def csvwrite(p,rows,fields=None):
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def csvread(p):return list(csv.DictReader(Path(p).open()))
def mdtable(fields,rows):
    def cell(x):return str(x if x is not None else MISSING).replace('|',' / ').replace('\n',' ')
    return ['|'+'|'.join(fields)+'|','|'+'|'.join('---' for _ in fields)+'|']+['|'+'|'.join(cell(r.get(k,MISSING)) for k in fields)+'|' for r in rows]

def exclusion(p):
    rel=p.relative_to(MERGE)
    if rel.parts[0]=='sealed-first-deliveries':return 'outside stage3: immutable T22/stages1-2 archives retained locally and not uploaded again'
    if p.name.endswith(('.mapping','.order.json')) or p.name in ['order.json','last-completed-sweep.checkpoint.json']:return 'bulk permutation/coarse mapping retained locally under >50MiB order policy'
    if set(rel.parts)&{'deps','.venv','venv','__pycache__','.private'}:return 'dependency/cache/private directory excluded from transfer'
    magic=p.open('rb').read(4)
    if magic in [b'\x7fELF',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xce',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'] or magic[:2]==b'MZ':return 'compiled executable/shared library retained locally; source/build/load SHA evidence kept'
    if p.suffix.lower() in ['.so','.dylib','.dll','.exe','.o','.a','.pyc']:return 'compiled artifact retained locally; not included in transfer'
    return None

def supplements(states,meta):
    dst=ROOT/'supplements';dst.mkdir()
    residual=[]
    for m in meta:
        degrees=np.load(BASE/'work/matrices'/m['matrix']/'degrees.npy',mmap_mode='r')
        assert len(degrees)==m['n']
        for t in m['taus']:
            tau=t['tau'];mask=degrees<=tau;nr=int(np.count_nonzero(mask));nz=int(degrees[mask].sum(dtype=np.int64));assert nr==t['resid_count']
            n=m['n'];W=16;K=(n-nr+W-1)//W;NB=(n+W-1)//W;words=(K+63)//64;cw=(n+63)//64
            estimate=n*words*8+K*NB*2+K*cw*16+NB*words*16+m['nnz_A0']*48+K*1024
            residual.append(dict(matrix=m['matrix'],tau=tau,tau_rule=t['tau_rule'],residual_rows=nr,residual_nnz_A0=nz,residual_nnz_A1=nz+nr,n=n,W=W,K_windows=K,NB=NB,LS_preflight_bytes=estimate,budget_bytes=8*2**30,over_estimated_budget=estimate>8*2**30,
              value_kind='deterministic formula evaluated from saved degree array, not measured RSS',degrees_sha256=sha(BASE/'work/matrices'/m['matrix']/'degrees.npy'),co_chain_workspace_bytes=MISSING,co_chain_missing_reason='original vector capacities/pair enumeration not recorded; no layout rerun or reconstructed capacity estimate'))
    residual.append(dict(matrix='mycielskian15',tau=MISSING,tau_rule='input unavailable',residual_rows=MISSING,residual_nnz_A0=MISSING,LS_preflight_bytes=MISSING,value_kind='SKIPPED; official input unavailable'))
    csvwrite(dst/'residual-workspace.csv',residual)
    timing=[];rounds=[];conditions=[];incomplete=[]
    source_states={x['case_id']:x for x in states if x['scope']!='optional unavailable reference'}
    assignment=read(BASE/'handoff/T23-split-20261109/assignment.json')
    remote_ids={c['case_id'] for c in assignment['remote_cases']}
    post_methods={'B0','B1','C9-Gorder','C9-S','C10-BP','C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I','C1-J','C1-H','C5','C5-U','C8-METIS'}
    raw_details=defaultdict(list)
    for cid,state in source_states.items():
        if state['matrix'] not in ['reddit','ogbn-products']:continue
        hostroot=REMOTE if cid in remote_ids else BASE
        host=state['recorded_execution_host_id'];case=read(hostroot/'work/stage3-cases'/cid/'record.json')
        evidence=[state['reason'],case.get('error','')];command_list=[]
        gc=case.get('generation_command',{})
        if gc:command_list.append(gc);evidence += [gc.get('reason',''), 'exitcode='+str(gc.get('exitcode'))]
        for phase in ['eval','diag']:
            cp=hostroot/'logs'/f'stage3-{phase}-{cid}.command.json'
            if cp.exists():command_list.append(read(cp));evidence.append(read(cp).get('reason',''))
        for phase in ['stage3-evaluations']:
            rp=hostroot/'work'/phase/cid/'rows.json'
            if rp.exists():evidence += [r.get('note','') for r in read(rp)]
        if state['member'] in post_methods:
            m=next(x for x in meta if x['matrix']==state['matrix'])
            for t in m['taus']:
                tau=t['tau'];key=cid+'__tau'+str(tau);folder=hostroot/'work/post-e'/key
                rp=folder/'record.json';pr=read(rp) if rp.exists() else {}
                cp=folder/'last-completed-sweep.checkpoint.json';checkpoint=read(cp) if cp.exists() else {}
                rows=read(folder/'rows.json') if (folder/'rows.json').exists() else []
                command_path=hostroot/'logs'/f'stage3-post-{key}.command.json';command=read(command_path) if command_path.exists() else {}
                if command:command_list.append(command)
                evidence += [pr.get('error',''),pr.get('note',''),command.get('reason','')]+[r.get('note','') for r in rows]
                history=pr.get('diagnostics',{}).get('history') or checkpoint.get('history') or []
                origin=rp if pr.get('diagnostics',{}).get('history') else cp
                count=pr.get('diagnostics',{}).get('sweeps_done')
                scope='final record' if count is not None else 'last persisted completed-sweep history' if history else 'no complete sweep recorded'
                if count is None:count=len(history) if history else 0 if 'LS exact workspace preflight' in pr.get('error','') else MISSING
                base=dict(matrix=state['matrix'],candidate=state['member'],W=state['W'],tau=tau,host=host,post_case_id=key,
                  status=pr.get('status','INCOMPLETE'),completed_rounds=count,round_count_scope=scope,
                  post_command_seconds=command.get('actual_method_seconds',MISSING),post_pipeline_seconds=pr.get('seconds',MISSING),
                  PLS_seconds_separately=MISSING,D_greedy_seconds_separately=MISSING,tail_co_seconds_separately=MISSING,
                  missing_reason='only cumulative round elapsed and combined layout+metrics d_sec were logged; no subtraction/inference',
                  post_record=str(rp) if rp.exists() else MISSING,post_record_sha256=sha(rp) if rp.exists() else MISSING,
                  command_path=str(command_path) if command_path.exists() else MISSING)
                timing.append(base)
                for h in history:
                    rounds.append(dict(matrix=state['matrix'],candidate=state['member'],tau=tau,host=host,round_index=h['sweep'],round_seconds=MISSING,
                      cumulative_elapsed_seconds=h.get('elapsed',MISSING),completed_rounds=count,accepted=h.get('accepted',MISSING),source_path=str(origin),source_sha256=sha(origin),
                      note='cumulative elapsed is an original logged field, not a per-round duration; no differencing'))
                for r in rows:
                    conditions.append(dict(matrix=state['matrix'],candidate=state['member'],tau=tau,host=host,diag=r['diag'],d_rule=r['d_rule'],status=r['status'],
                      D_greedy_seconds=MISSING,tail_co_seconds=MISSING,recorded_combined_layout_metrics_d_sec=r.get('d_sec',MISSING),
                      recorded_post_sec=r.get('post_sec',MISSING),note='combined original timer preserved; no decomposition',rows_source=str(folder/'rows.json'),rows_sha256=sha(folder/'rows.json')))
        if state['status']=='INCOMPLETE':
            text='; '.join(str(v) for v in evidence);categories=[]
            if 'timeout' in text.lower() or any(c.get('exitcode')==124 for c in command_list):categories.append('超时')
            if any(s in text for s in ['workspace','safety budget','preflight']):categories.append('工作空间估算门槛')
            if any(c.get('exitcode') in [-9,-15,137,143] for c in command_list) or state['member']=='C8-METIS' and state['matrix']=='reddit':categories.append('被中断')
            # Historical RUNNING on the preserved reboot-interrupted C8 command
            # is not interpreted as an actually running or queued task.
            assert categories,(cid,text)
            incomplete.append(dict(case_id=cid,matrix=state['matrix'],candidate=state['member'],W=state['W'],seed=state['seed'],host=host,
              primary_category=categories[0],all_categories=' / '.join(categories),original_status='INCOMPLETE',original_reason=state['reason'],
              supporting_saved_errors=text,interruption_note='original SIGKILL source unconfirmed; not asserted OOM' if any(c.get('exitcode')==-9 for c in command_list) else 'reboot interruption has no invented exit code' if state['member']=='C8-METIS' and state['matrix']=='reddit' else '',
              current_state='terminal; no retry; no case currently queued'))
    assert len(timing)==64 and len(incomplete)==48
    csvwrite(dst/'post-E-timing.csv',timing);csvwrite(dst/'PLS-round-times.csv',rounds);csvwrite(dst/'post-E-condition-times.csv',conditions);csvwrite(dst/'INCOMPLETE-cases.csv',incomplete)
    formula='''# 工作空间公式（估算，不是实测 RSS）

8 GiB = 8589934592 bytes。LS 在分配前使用固定安全估算：
n*ceil(K/64)*8 + K*NB*2 + K*ceil(n/64)*16 + NB*ceil(K/64)*16 + nnz(A0)*48 + K*1024。
K=ceil((n-residual_rows)/W), NB=ceil(n/W)，本表W=16。残余集合按A0度<=τ固定，A1残余非零=A0残余非零+残余行数。
residual-workspace.csv具体数值来自保存的degrees.npy和原公式；没有启动LS或评价器。

v7 co-chain flat table上界 bound=min(枚举点对数, P*(P-1)/2,100000001)。
capacity为满足 capacity*7>=bound*10 的最小2次幂。
估算=上下文及工作向量的实际capacity字节 + capacity*(8+4) + bound*sizeof(tuple<int,int,int>) + 1073741824。
只有估算<=8GiB才走flat表，否则回退到原map；map独特点对>100000000触发带8GiB估算文字的错误。
原进程的向量capacity/点对枚举未完整记录，因此不补造每个co-chain条件的字节值，具体数值标缺失。
inter候选数>200000000也有工作空间保护。上述门槛均不能替代峰值RSS实测。
原始公式与哈希见formula-sources/，无新算布局/LS/D。
'''
    (dst/'workspace-formulas.md').write_text(formula)
    for n in ['ls_runtime.py','layouts_flatco.cpp','native_chain_v6.py','post_e_job.py']:copy(BASE/'scripts'/n,dst/'formula-sources'/n)
    return residual,incomplete,len(rounds),len(conditions)

def main():
    assert not ROOT.exists(),'never overwrite a sealed directory'
    assert read(BASE/'merge-hostb-20261110/final-verification.json')['passed']
    receipt=read(BASE/'merge-hostb-20261110/merge-receipt.json')
    for r in [receipt['results'],receipt['orders']]:assert sha(r['path'])==r['sha256']
    ROOT.mkdir(parents=True)
    exclusions=[];copied=[]
    for p in sorted(MERGE.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(MERGE)
        if len(rel.parts)==1 and p.name in ['README.md','manifest.json','SHA256SUMS']:continue
        reason=exclusion(p)
        if reason:
            exclusions.append(dict(original_path=str(p),relative_source_path=str(rel),bytes=p.stat().st_size,sha256=sha(p),reason=reason));continue
        copy(p,ROOT/rel);copied.append(dict(path=str(rel),source_path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
    copy(MERGE/'manifest.json',ROOT/'provenance/merge-manifest.json');copy(MERGE/'README.md',ROOT/'provenance/merge-README.md')
    csvwrite(ROOT/'excluded-files.csv',exclusions)
    dump(ROOT/'formalization-copy-proof.json',dict(scope='new formal stage3 release from verified terminal merge; existing files unchanged',copied_unchanged=copied))
    states=csvread(ROOT/'status.csv');core=[r for r in states if r['scope']!='optional unavailable reference'];assert len(core)==409 and all(r['attempted']=='True' for r in core)
    rows=csvread(ROOT/'results.csv');assert len(rows)==6276
    meta=read(BASE/'logs/matrices-and-taus.json')
    residual,incomplete,nround,nconditions=supplements(states,meta)
    inputs=[]
    for m in meta:
        p=Path(m['input_path']);h=sha(p)
        if m['matrix'] in ['reddit','ogbn-products']:
            f=read(BASE/'logs'/('fetch-reddit_graph.json' if m['matrix']=='reddit' else 'fetch-products-edge.csv.json'));assert h==f['sha256']
        else:assert h==m['input_mtx_sha256']
        inputs.append(dict(matrix=m['matrix'],source_url=m['source_url'],sha256=h,input_file=str(p),n=m['n'],stored_entries=m['stored_entries'],diagonal_entries=m['diagonal_entries'],nnz_A0=m['nnz_A0'],explicit_zero_entries=m['explicit_zero_entries'],
          T19_reference_n=2449029 if m['matrix']=='ogbn-products' else '',T19_reference_nnz=114615892 if m['matrix']=='reddit' else 123718152 if m['matrix']=='ogbn-products' else '',
          nnz_A0_minus_T19=0 if m['matrix']=='reddit' else -128 if m['matrix']=='ogbn-products' else '',
          note='128 original diagonal storage entries removed by fixed A0; symmetric expansion/dedup preserved' if m['matrix']=='ogbn-products' else 'reconstructed numbering and explicit zeros retained; B0/P11 reference-only' if m['matrix']=='wiki-RfA' else ''))
    inputs.append(dict(matrix='mycielskian15',source_url='SuiteSparse official index https://sparse.tamu.edu/ and original failed-download logs',sha256=MISSING,n=MISSING,stored_entries=MISSING,diagonal_entries=MISSING,nnz_A0=MISSING,explicit_zero_entries=MISSING,note='official download failed (403/TLS/404); no input bytes or invented tau; SKIPPED'))
    csvwrite(ROOT/'matrix-inputs.csv',inputs)
    guards=csvread(ROOT/'guard-counts.csv');grouped=defaultdict(list)
    for r in guards:
        if r.get('co_chain_guard_windows_skipped','')!='':grouped[(r['matrix'],r['W'],r['tau'])].append(int(r['co_chain_guard_windows_skipped']))
    guard_summary=[dict(matrix=k[0],W=k[1],tau=k[2],reported_conditions=len(v),min_windows=min(v),max_windows=max(v),sum_reported_windows=sum(v),scope='per-condition reported counts; cached repeats not independent physical scans') for k,v in sorted(grouped.items())]
    csvwrite(ROOT/'co-chain-guard-summary.csv',guard_summary)
    orders=read(MERGE/'orders-manifest.json');new=[r for r in orders['files'] if r['kind']=='new'];reuse=[r for r in orders['files'] if r['kind']=='reused'];assert len(new)==269 and len(reuse)==117
    for r in orders['files']:assert sha(r['path'])==r['sha256']
    new_bytes=sum(r['size'] for r in new);assert new_bytes==638252226
    (ROOT/'orders').mkdir();(ROOT/'orders/README.md').write_text(f'本阶段新行序269份，合计{new_bytes}字节，超过50MiB，全部只留本地。逐份原路径、大小、SHA256见../orders-manifest.json。复用117条仅引用不复制。\n本地完整行序包：{receipt["orders"]["path"]}\n包SHA256：{receipt["orders"]["sha256"]}\n该包还含复用引用和检查点，不把它的压缩大小称为新行序原始字节数。\n')
    # Preserve complete checkpoint and Rabbit maps locally; archive small sidecars.
    checkpoints=read(MERGE/'checkpoints-manifest.json');sides=[]
    for i,r in enumerate(checkpoints):
        p=Path(r['source']);assert sha(p)==r['sha256'];d=read(p);vector=d.pop('row_perm');assert len(vector)==next(m['n'] for m in meta if m['matrix'] in p.parent.name)
        side=dict(kind='derived metadata only; original complete vector retained locally',source_path=str(p),source_sha256=r['sha256'],source_size=r['size'],permutation_length=len(vector),checkpoint_metadata=d,original_status_not_promoted=True)
        dest=ROOT/'checkpoint-metadata'/f'{i:03d}-{p.parent.name}.json';dump(dest,side);sides.append(dict(r,metadata_path=str(dest.relative_to(ROOT)),metadata_sha256=sha(dest)))
    dump(ROOT/'checkpoints-manifest.json',sides)
    rabbit=[]
    for p in sorted((BASE/'work/rabbit-coarse').glob('*.mapping')):
        if not p.name.startswith(('reddit-','ogbn-products-')):continue
        rabbit.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),storage='local-only intermediate vertex permutation, not a new independent row order'))
    assert len(rabbit)==4;dump(ROOT/'rabbit-coarse-manifest.json',rabbit)
    for p in (BASE/'logs').glob('software-versions-*.json'):copy(p,ROOT/'environment'/p.name)
    copy(REMOTE/'logs/remote-port-preparation.json',ROOT/'environment/hostB-preparation.json')
    copy(REMOTE/'logs/hostB-environment.txt',ROOT/'environment/hostB-environment.txt')
    copy(BASE/'logs/stage3-start.json',ROOT/'provenance/stage3-start.json')
    copy(BASE/'logs/stage3-reboot-routing-gate.json',ROOT/'provenance/reboot-routing-gate.json')
    copy(BASE/'merge-hostb-20261110/final-verification.json',ROOT/'provenance/merge-final-verification.json')
    sys.path.insert(0,str(BASE/'scripts'))
    from audit_results import audit
    from artifact_pack import source_proof
    arithmetic=audit(ROOT/'results.csv');dump(ROOT/'formal-arithmetic-audit.json',arithmetic);frozen=source_proof();assert frozen['verified_original_files']==263
    expected_core=Counter(r['status'] for r in core);assert expected_core=={'OK':320,'INCOMPLETE':48,'SKIPPED':41}
    manifest=dict(experiment='T23 stage3 formal terminal-evidence release',run_date=DATE,sealed=True,all_cases_terminal=True,not_an_inprogress_snapshot=True,
      formalization_date=dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),source_repository=frozen,coverage=read(MERGE/'coverage.json'),
      case_status_counts=dict(expected_core),result_row_status_counts=dict(Counter(r['status'] for r in rows)),optional_reference_skipped=6,
      matrices=meta,new_orders=dict(count=269,total_bytes=new_bytes,local_only=True,full_inventory='orders-manifest.json'),reused_orders=dict(count=117,copied=False),
      new_order_bulk_receipt=receipt['orders'],excluded_file_count=len(exclusions),raw_results_original_bytes_preserved=True,
      incomplete_policy='dispatch section8; terminal failures retained, no retries/parameter changes; saved partial history reported without new LS/D or guessed missing times',
      partial_checkpoint_numeric_recovery='not performed; user forbids reruns; original tracked checkpoint numbers remain historical evidence, not newly verified output',
      native_binaries='retained locally; source/build/load hashes in raw evidence; excluded-files.csv lists removed transfer material',
      hosts=read(MERGE/'manifest.json')['hosts'],git_transfer_authorization='user explicit new orphan branch only; overrides historical dispatch no-push restriction for this transfer')
    dump(ROOT/'manifest.json',manifest)
    lines=[f'# T23 阶段3正式结果：{NAME}','','全部409例已有真实终止记录；不是运行中快照。按派发§8保留超时/中断/工作空间失败为INCOMPLETE，不重跑、不调参。',
      '',f'整例：320 OK / 48 INCOMPLETE / 41 SKIPPED；另6个可选参照SKIPPED。正式条件6276行：5396 OK / 588 INCOMPLETE / 292 SKIPPED。',
      '', '本目录是2026-11-10对已核验双主机终止证据的正式封存。原合并包与T21/T22/阶段1–2全部不改。数值表逐字节复制；只新增清单、README和补充材料。',
      '', '## 下载与合并校验','','```sh',f'cat {NAME}.tar.gz.part* > {NAME}.tar.gz','sha256sum -c SHA256SUMS','```',
      '', '分支根SHA256SUMS覆盖完整tar.gz与分片；解包后目录内SHA256SUMS覆盖所有正式文件（自身除外）。raw/内原始主机清单是历史证据，可能指向仅本地保留的ELF/行序，请以正式目录根清单核验本包。',
      '', '## 输入与T19差异','', '结构按存储条目定义，显式零保留；A0去对角/固定对称处理，A1按定义加I，残余集合按A0度数固定。',
      'Reddit实测nnz(A0)=114615892，与T19一致；products点数2449029，与T19一致，nnz(A0)=123718024，比T19的123718152少128。原始边表实测128个对角存储条目，不用“64个自环”的旧推测替代实测；未为匹配引用值改图。',
      'mycielskian15下载失败，不能提供输入SHA/实算规模/τ；相关条件SKIPPED，不用引用规模冒充实测。','']
    lines+=mdtable(['matrix','n','stored_entries','diagonal_entries','nnz_A0','explicit_zero_entries','sha256','source_url'],inputs)
    lines+=['','## τ实算、残余与工作空间','','8GiB为安全估算门槛，不是实测内存。LS公式与co-chain公式/缺失原因见supplements/workspace-formulas.md；每τ的具体数值见下表及CSV。','']
    lines+=mdtable(['matrix','tau','tau_rule','residual_rows','residual_nnz_A0','LS_preflight_bytes','over_estimated_budget'],residual)
    lines+=['','## co_chain守卫窗口数','','单窗口残余点>400触发跳过。以下是保存的逐条件报告数，含缓存继承，求和不是独立物理扫描次数。失败前未记录计数的条件保持缺失，不能当0；完整原报告与主机说明见guard-counts.csv。','']
    lines+=mdtable(['matrix','W','tau','reported_conditions','min_windows','max_windows','sum_reported_windows'],guard_summary)
    lines+=['','## 环境、工具与阶段1–2差异','','阶段1–2主机为macOS15.2 arm64/M1 Pro16GiB，Python3.12.10、NumPy2.4.4、SciPy1.17.1、Apple clang16；本阶段hostA相同。',
      '新增hostB为Windows/WSL2 Linux6.18.54.1 x86_64、AMD Ryzen7 5800H，Python3.12.3、NumPy2.4.4、SciPy1.17.1、g++13.3.0；原RSS KiB→MiB适配与11项新WSL门禁已核验。每行保留实际主机，跨主机时间不混合平均。',
      '外部依赖：PyNNDescent0.7.0 / numba0.68.1 / llvmlite0.50.0 / pymetis2025.2.2 / KaHyPar1.3.7。hostA隔离外部依赖NumPy2.5.4、SciPy1.18.1，与主评价环境不同，原版本JSON/扩展SHA均保留。',
      'Rabbit锁定作者ref f93776e9c1e1d4a8962ee56bc7ff0091e6fe12dd，Linux ARM guest、Boost1.58、gperftools2.16、libnuma2.0.18，OMP=1，无随机种子API。hostB的-R复用hostA历史Rabbit-U粗序，order_sec可能含历史coarse_seconds；当前local_seconds另见原记录，不能视为WSL总实测。',
      'v2→v7缓存/计数实现按原启用时间保留；不把新库追用于早期进程。原命令、导入源码SHA与实际加载DLL/ELF SHA分主机保存。','',
      '## 行序与排除内容','',f'新算269份，{new_bytes}字节（>50MiB），全部只留本地；复用117条仅引用，未复制到orders/。逐份大小、来源与SHA256见orders-manifest.json。',
      f'本地完整行序/检查点包：{receipt["orders"]["path"]}；{receipt["orders"]["size"]}字节；SHA256 `{receipt["orders"]["sha256"]}`。该本地包不上传。',
      f'排除{len(exclusions)}项，见excluded-files.csv（原路径/字节数/SHA256/理由）：编译库/可执行文件、批量排列/粗排映射以及非阶段3旧封存包。原件均保留，源码与构建/加载哈希仍可核验。',
      '', '## 补充计时与INCOMPLETE分类','',f'64个post-E组合，{nround}条已记录完整轮次；逐轮秒数未独立记录，明确标缺失，只附原始累计elapsed，不作差。D-greedy与tail-co独立秒数同样缺失；{nconditions}条原始combined d_sec仅标为layout+metrics总计时，不能冒充分段。',
      'supplements/INCOMPLETE-cases.csv覆盖48例，按超时/工作空间估算门槛/被中断归类，可多原因；当前无排队中。products C6-HP原exit -9归“被中断”，来源未证实，不称为实测OOM；Reddit C8-METIS保留τ53超时和τ153重启中断，无伪造退出码。',
      '原完成轮次检查点完整向量仅本地保留，包内为明确标注的派生元数据。未执行检查点LS/D/评价重跑，未把其tracked数值提升为新验证结果；原INCOMPLETE仍INCOMPLETE。','',
      '## 矩阵 × 候选 × W 状态表','','覆盖全部409正式例与6可选参照；其中包含reddit/products/mycielskian15及W32/64/128敏感性，不把生成OK等同整例OK。','']
    lines+=mdtable(['matrix','member','W','seed','status','reason'],states)
    (ROOT/'README.md').write_text('\n'.join(lines)+'\n')
    copy(Path(__file__),ROOT/'provenance/formalize-transfer.py')
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=ROOT/'SHA256SUMS']
    (ROOT/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in files))
    # Byte identity of every existing numeric table, not merely row totals.
    for n in ['results.csv','status.csv','diag.csv','groups.csv','guard-counts.csv','post-E.csv']:assert sha(ROOT/n)==sha(MERGE/n)
    archive=OUT/(NAME+'.tar.gz');assert not archive.exists()
    with tarfile.open(archive,'w:gz',compresslevel=6) as t:t.add(ROOT,arcname='第一层实验结果/'+NAME)
    with tarfile.open(archive) as t:
        prefix='第一层实验结果/'+NAME+'/'
        expected={prefix+line.split('  ',1)[1]:line.split('  ',1)[0] for line in (ROOT/'SHA256SUMS').read_text().splitlines()}
        actual={m.name for m in t.getmembers() if m.isfile()};assert actual==set(expected)|{prefix+'SHA256SUMS'}
        for n,h in expected.items():assert hashlib.file_digest(t.extractfile(n),'sha256').hexdigest()==h,n
    receipt=dict(sealed=True,formal_directory=str(ROOT),archive=str(archive),archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),file_count=len(files)+1,original_directory_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()),excluded_files=len(exclusions),case_counts=dict(expected_core),branch='transfer/t23-stage3-'+DATE,over_1_5_GiB=archive.stat().st_size>int(1.5*2**30),no_scientific_rerun=True)
    dump(OUT/'formal-seal-receipt.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
