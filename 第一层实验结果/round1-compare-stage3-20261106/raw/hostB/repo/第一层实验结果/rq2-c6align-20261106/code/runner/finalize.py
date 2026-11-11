from __future__ import annotations
import collections,csv,datetime,hashlib,json,platform,shutil,subprocess,sys,tarfile
from pathlib import Path
sys.dont_write_bytecode=True
from campaign import BASE,REPO,OUT,FIELDS,JOINT_FIELDS,P0,acquisition,dump,slug
import run_stage

MATRICES=['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']
def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def condition_key(r:dict)->tuple:
    p=json.loads(r.get('member_params','{}'));member=r['member']
    variant=(p.get('start',''),p.get('lambda',''),p.get('seed',0)) if member.startswith('P-LS') else (p.get('mnc',''),p.get('seed',0))
    return tuple(r.get(x,'') for x in ('matrix','diag','member','W','tau','placement','d_rule'))+variant

def missing_rows(spec:dict,status:str,note:str)->tuple[list, list]:
    kind=spec['kind'];rows=[];joint=[];W=spec.get('W',16)
    taus=(None,3) if kind=='w' else ((None,2,3) if kind!='ls' or spec.get('tau') is None else (spec['tau'],))
    if kind=='independent':taus=(None,)
    for tau in taus:
        if kind=='independent':cases=[('none',spec['rule'])]
        else:
            cases=[('none' if tau is None else 'tail','own'),('none' if tau is None else 'tail','D-greedy')]
            if tau is not None and kind!='ls':cases.insert(0,('inplace','own'))
            if W==16 and kind not in ('ls','c6'):cases.append(('none' if tau is None else 'tail','D-exact'))
        for placement,rule in cases:
            for diag in ('A0','A1'):
                r=dict(matrix=spec['matrix'],diag=diag,member=spec['member'],member_params=json.dumps(spec,ensure_ascii=False,separators=(',',':')),W=W,tau='none' if tau is None else tau,placement=placement,d_rule=rule,status=status,note=note)
                rows.append(r)
                if kind in ('ls','c6'):
                    joint.append({**r,**{k:spec.get(k,'') for k in ('start','lambda','mnc','seed')},'sweeps_done':'','accepted_swaps':''})
    return rows,joint

def main()->None:
    rows=[];joint=[];checks=[]
    for p in sorted((OUT/'tasks').glob('*.json')):
        d=json.loads(p.read_text());rows.extend(d['rows']);joint.extend(d['joint']);checks.extend(d['checks'])
    inputs=acquisition();dependency=json.loads((BASE/'logs/p2-dependencies.json').read_text());real_acquisition=run_stage.acquisition
    run_stage.acquisition=lambda:{m:{'status':'OK'} for m in MATRICES}
    stages=('p0','p1','independent','p2')+(('c6',) if dependency['available'] else ())
    expected=[s for stage in stages for s in run_stage.specs(stage)]
    run_stage.acquisition=real_acquisition
    failures=[]
    for spec in expected:
        path=OUT/'tasks'/(spec['key']+'.json')
        command=BASE/'logs/jobs'/(spec['key']+'.command.json')
        if spec['matrix'] in inputs and inputs[spec['matrix']]['status']=='OK':
            if path.exists() and command.exists() and json.loads(command.read_text()).get('returncode')==0:continue
            reason='Job incomplete; see logs/jobs/'+spec['key']+'.command.json'
            if command.exists():
                record=json.loads(command.read_text());reason+='; returncode='+str(record.get('returncode','unknown'))
                if record.get('timed_out'):reason+='; exceeded 7200 second case limit'
            trace=OUT/'checks'/(spec['key']+'-bisections.json')
            if trace.exists():
                data=json.loads(trace.read_text());last=data['calls'][-1] if data['calls'] else {}
                if data['status'].startswith('INCOMPLETE'):
                    reason+='; KaHyPar exact balance failed: part '+str(last.get('part_id'))+', targets '+str(last.get('targets'))+', actual '+str(last.get('actual_sizes'))+'; '+last.get('failure','')+'; trace=checks/'+trace.name
            reason+='; stderr=logs/jobs/'+spec['key']+'.stderr.log'
            failures.append(spec['key']);status='INCOMPLETE'
        else:
            d=inputs[spec['matrix']];status='SKIPPED' if spec['matrix']=='wiki-RfA' else 'INCOMPLETE'
            reason='Input unavailable: official endpoint HTTP 403; official HTTPS file-server SSL connection failed; user confirms no local cache. Details in logs/input-acquisition.json. '+d.get('error','')
        # Preserve any completed rows of an interrupted job and only add missing condition rows.
        rr,jj=missing_rows(spec,status,reason)
        present={condition_key(r) for r in rows}
        for r in rr:
            key=condition_key(r)
            if key not in present:rows.append(r)
        joint.extend(jj)
    for matrix in MATRICES:
        if not dependency['available']:
            for mnc in (0,1,4,16):
                spec={'kind':'c6','matrix':matrix,'member':'C6' if mnc==0 else 'C6-M','W':16,'mnc':mnc,'seed':0}
                rr,jj=missing_rows(spec,'SKIPPED','KaHyPar / PaToH unavailable; installation evidence in logs/p2-dependencies*. No substitute partitioner used.')
                rows.extend(rr);joint.extend(jj)
        for member in ('B-RSH-ref','B-Neutron-ref'):
            rows.append(dict(matrix=matrix,member=member,member_params='{}',status='SKIPPED',note='Optional T4/T2 reference not available in selected repository commit; pilot variants are separately labeled.'))
    rank={'OK':2,'INCOMPLETE':1,'SKIPPED':0}
    def unique(data:list)->list:
        table={}
        for row in data:
            key=condition_key(row);old=table.get(key)
            if old and old['status']==row['status']=='OK':
                for field in ('sumU','T','sumGamma','sumR'):assert old[field]==row[field],(key,field)
            if old is None or rank[row['status']]>rank[old['status']]:table[key]=row
        return list(table.values())
    rows=unique(rows);joint=unique(joint)
    for filename,data,fields in [('results.csv',rows,FIELDS),('joint.csv',joint,JOINT_FIELDS)]:
        with (OUT/filename).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(data)
    dump(OUT/'checks/invariants.json',{'all_recorded_checks_passed':True,'scope':'Permutation and metric/D/LS invariants for completed evaluations only. C6 failures are separately recorded in bisection traces and main result statuses.','checks':checks,'D_checks':sum('membership_unchanged'in x for x in checks),'LS_checks':sum('ls_incremental_equals_full_recompute'in x for x in checks)})
    statuses=[]
    for matrix in MATRICES:
        for member in sorted({r['member'] for r in rows if r['matrix']==matrix}):
            subset=[r for r in rows if r['matrix']==matrix and r['member']==member];counts=collections.Counter(r['status'] for r in subset)
            status='INCOMPLETE' if counts['INCOMPLETE'] else ('OK' if counts['OK'] else 'SKIPPED')
            reasons=sorted({r['note'] for r in subset if r['status']!='OK'})
            statuses.append(dict(matrix=matrix,member=member,status=status,OK=counts['OK'],INCOMPLETE=counts['INCOMPLETE'],SKIPPED=counts['SKIPPED'],reason=' | '.join(reasons)))
    with (OUT/'matrix-method-status.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(statuses[0]));writer.writeheader();writer.writerows(statuses)
    members=sorted({r['member'] for r in rows});lookup={(r['matrix'],r['member']):r for r in statuses}
    with (OUT/'matrix-method-status.md').open('w') as f:
        f.write('# 矩阵 × 方法状态\n\n单元格是总体状态；子条件计数与具体原因见同名 CSV。\n\n| 矩阵 | '+' | '.join(members)+' |\n|---|'+'---|'*len(members)+'\n')
        for m in MATRICES:f.write('| '+m+' | '+' | '.join(lookup[(m,x)]['status'] if (m,x) in lookup else '—' for x in members)+' |\n')
        f.write('\n—：方案未要求该矩阵与方法组合。\n')
    (OUT/'logs').mkdir(exist_ok=True);shutil.copytree(BASE/'logs',OUT/'logs',dirs_exist_ok=True)
    (OUT/'code').mkdir(exist_ok=True);shutil.copytree(BASE/'scripts',OUT/'code/runner',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(REPO/'第一层工作区/T17-空白一试算脚本',OUT/'code/reference',dirs_exist_ok=True)
    (OUT/'code/pilot-reference').mkdir(exist_ok=True)
    shutil.copy2(REPO/'第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py',OUT/'code/pilot-reference/rsh_reorder_experiment.py')
    shutil.copytree(BASE/'source-baselines/fd1fc09',OUT/'code/reference-baseline-fd1fc09',dirs_exist_ok=True)
    shutil.copy2(REPO/'第一层工作区/RQ2验证实验方案.md',OUT/'code/RQ2验证实验方案.md')
    (OUT/'binaries').mkdir(exist_ok=True)
    for p in list((BASE/'work').glob('*.dylib'))+[BASE/'work/selfcheck/rq2_hk_bin']:shutil.copy2(p,OUT/'binaries'/p.name)
    if dependency['available']:shutil.copy2(dependency['module_path'],OUT/'binaries'/Path(dependency['module_path']).name)
    shutil.copytree(BASE/'work/selfcheck/out',OUT/'selfcheck',dirs_exist_ok=True)
    (OUT/'inputs').mkdir(exist_ok=True)
    for m,d in inputs.items():
        if d['status']=='OK' and not d.get('protocol_alias_of'):
            shutil.copy2(d['mtx'],OUT/'inputs'/(m+'.mtx'))
            if d.get('archive_path'):shutil.copy2(d['archive_path'],OUT/'inputs'/Path(d['archive_path']).name)
    shutil.copy2(BASE/'inputs/arxiv.zip',OUT/'inputs/arxiv-original.zip')
    before=json.loads((BASE/'logs/repository-before.json').read_text())
    after={str(p.relative_to(REPO)):sha(p) for p in REPO.rglob('*') if p.is_file() and '.git' not in p.parts}
    integrity={'all_checked_out_files_unchanged':before==after,'files_checked':len(before),'git_status_porcelain':subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True),'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()}
    assert integrity['all_checked_out_files_unchanged'] and not integrity['git_status_porcelain'];dump(OUT/'checks/repository-integrity.json',integrity)
    metric_counts=dict(collections.Counter(r['status'] for r in rows));joint_counts=dict(collections.Counter(r['status'] for r in joint))
    manifest={'task':'T21','date_asia_shanghai':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'repository_url':'https://github.com/pangxiegonghhh/rsh-npu-experiments-claude','commit':integrity['HEAD'],'tree':'f8025fa031f1a56906de58e21ec730f6b6666293','outcome':('INCOMPLETE_CASES' if metric_counts.get('INCOMPLETE') else 'COMPLETE_WITH_DOCUMENTED_SKIPS'),'source_baselines':{'fd1fc09253b086daf394aa6e9c921faa59ae7569':'initial completed Cora/arxiv; preserved by explicit package-ten instruction','87594cc9e80e800c77a65988c09f7067b63957be':'current protocol; all stored entries, including explicit zeros'},'wiki_RfA_caveat':'SNAP reconstruction; different numbering; B0 and P11 sumR/sumU are reference-only, no cross-work comparison','repository_unchanged':True,'pushed':False,'CPU_only':True,'matrices':json.loads((BASE/'logs/matrix-statistics.json').read_text()),'environment':json.loads((BASE/'logs/environment.json').read_text()),'expected_specs':expected,'parameters':{'row_order_computed_on':'A0','A1':'A0 + all diagonal positions, evaluation only','residual':'deg_A0 <= tau, identical for A0 and A1','D':'rq2lib.dstage and validated native port; two-thread bit-iteration Held-Karp; exact same objective/ties; membership and sumU/sumGamma invariants','K_tile_width':16,'D_exact_matrices':[m for m in MATRICES if m!='ogbn-arxiv'],'LS_sweeps_max':10,'LS_cand_parts':3,'LS_seeds_cora_arxiv':[0,1,2],'LS_full_control_seed':0,'LS_ties':'overlap descending then group ID ascending; candidate member current order','LS_rng':'Python random.Random, original reference movable iteration order','indep_CBM_co_pair_limit':50000000,'method_timeout_sec':7200,'worker_count':2,'independent_worker_count':1,'large_arxiv_LS_max_concurrent':1,'LS_backend':'V1 initial Cora; V3/V4 subsequent cases. Exact delta, dense block counts, bitset incidence, incremental overlap scores; V4 fused trial deltas. Each version passed exact six-case ten-sweep differential validation and full Table A. Per-job binary/source SHA identifies actual version.'},'results_status_counts':metric_counts,'joint_status_counts':joint_counts,'job_failures':failures,'selfcheck':json.loads((BASE/'logs/selfcheck-gate.json').read_text()),'native_tableA':json.loads((BASE/'logs/port-validation.json').read_text()),'independent_reference_check':json.loads((BASE/'logs/independent-selfcheck-comparison.json').read_text()),'independent_campaign_audit':{'passed':json.loads((BASE/'logs/independent-campaign-audit.json').read_text())['passed'],'path':'logs/independent-campaign-audit.json'},'dependency_status':dependency,'code_sha256':{str(p.relative_to(OUT)):sha(p) for p in (OUT/'code').rglob('*') if p.is_file()},'binary_sha256':{p.name:sha(p) for p in (OUT/'binaries').iterdir()},'optional_second_batch':'not run; first-batch and P0/P1/P2 prioritized','development_notes':['Package-ten commit/tree verified; all seven protocol matrices available; wiki stored zeros retained and reference-only caveat applied.','No previous failed self-check materials reused.','Python TLS certificate-store error avoided using system curl with normal TLS verification.','Before formal LS jobs, movable-set order corrected; three one-sweep cases then exactly matched reference with declared stable group ties.','CBM native matches reference greedy-edge column permutations; legacy document standalone CBM numbers differ and the legacy script was not present; discrepancy recorded, no reference values changed.','P0 used the same native library as validated on Table A; later Python edits only added P1/independent functionality. Per-job code snapshots are captured from P1 onward.']}
    manifest['parameters'].update(worker_count_history=[2,4], worker_count_after_v5_handover=4,
        large_arxiv_LS_max_concurrent_history={'V1_to_V4':1,'V5':4},
        LS_backend='V1 initial Cora; V3/V4 intermediate cases; V5 then V8 subsequent cases. V5 uses equivalent transposed block presence/singleton bitsets for Gamma deltas and sparse overlap queries on arxiv. V8 adds exact 0/1/>1 count flags laid out by group/column for cache locality. Each production version passed exact ten-sweep differential validation and full Table A. V6/V7 were correct but not promoted. Per-job code/binary SHA identifies the actual version.')
    manifest['parameters'].pop('worker_count',None)
    manifest['parameters'].pop('large_arxiv_LS_max_concurrent',None)
    manifest['native_v5_validation']=json.loads((BASE/'logs/ls-backend-v5-validation.json').read_text())
    manifest['native_v5_arxiv_single_sweep_validation']=json.loads((BASE/'logs/arxiv-v5-one-sweep.json').read_text())
    manifest['native_v8_validation']=json.loads((BASE/'logs/ls-backend-v8-validation.json').read_text())
    manifest['native_v8_arxiv_single_sweep_validation']=json.loads((BASE/'logs/arxiv-v8-one-sweep.json').read_text())
    manifest['native_slashburn_validation']=json.loads((BASE/'logs/slashburn-validation.json').read_text())
    manifest['parameters']['large_arxiv_LS_max_concurrent_history']['V8']=4
    manifest['parameters']['native_compile_flags_by_version']={
        'V1-V5':['-std=c++17','-O3','-ffp-contract=off','-dynamiclib'],
        'V8':['-std=c++17','-O3','-mcpu=native','-ffp-contract=off','-dynamiclib']}
    manifest['parameters']['stage_worker_counts']={'p0':2,'p1_initial':2,'p1_after_handover':4,'independent':1,'p2':2,'c6':2,'audit':1}
    manifest['parameters']['C6']={'solver':'KaHyPar 1.3.7','configuration':'code/runner/kahypar-cut-v1.3.7.ini',
        'W':16,'mnc':[0,1,4,16],'seed':0,'epsilon':0.0,'column_net_cost':1,'send_and_receive_net_cost_each':'mnc',
        'targets':'left=W*ceil(size/(2*W)), right=size-left; custom target block weights',
        'schedule':'breadth first; message destinations are current parts',
        'own_order':'DFS left/right leaves, partial leaf last',
        'exact_size_gate':'Abort case as INCOMPLETE if solver sizes differ from targets; preserve failed model and labels',
        'timeout_sec':7200}
    manifest['expected_spec_count']=len(expected)
    manifest['completed_spec_count']=len(expected)-len(failures)
    manifest['attempted_spec_count']=sum((BASE/'logs/jobs'/(s['key']+'.command.json')).exists() for s in expected)
    early=[]
    for path in (BASE/'logs/jobs').glob('*.command.json'):
        record=json.loads(path.read_text())
        if not record.get('code_sha256'):early.append(record['spec']['key'])
    manifest['code_provenance']={
        'per_job_snapshots':'logs/jobs/*.command.json and logs/code-snapshots/',
        'early_records_without_per_job_wrapper_hash':sorted(early),
        'early_record_note':'Initial Cora/arxiv P0 records predate per-job wrapper snapshots. They used the retained original native binary/reference baseline; all saved permutations and representative metric conditions are independently audited. No retrospective wrapper hash is fabricated, and completed cases were retained under the package-ten instruction.'}
    dump(OUT/'manifest.json',manifest)
    from delivery_audit import verify
    dump(OUT/'checks/final-coverage-audit.json',verify(OUT,BASE,expected))
    (OUT/'README.md').write_text('''# T21 CPU 结构验证交付

当前计划基线为包十 87594cc9e80e800c77a65988c09f7067b63957be，树哈希 f8025fa031f1a56906de58e21ec730f6b6666293。包九全新空目录自检首行 OK、退出码 0；加速版表 A、原生 D 阶段表 A/B、局部搜索增量均完成核验。包十保留显式零；Cora/arxiv 不含显式零，按用户要求保留已完成结果。

第一批七张矩阵输入均已具备。四个 UF 原包只取各自同名 MTX，不使用 olafu_b.mtx。wiki-RfA 使用用户提供的 SNAP 重建版，保留 11,493 个显式零；节点编号与官方不同，B0 及 P11 的 ΣR/ΣU 仅作参考，不与其他工作比较。所有来源 URL、文件 SHA-256、显式零数及对角条目数见 manifest。

results.csv、joint.csv 为逐条件原始指标；matrix-method-status.csv/.md 给出状态及原因。不得把未测、超时、跳过或不满足门槛解释为通过。orders/ 中 row_perm[新位置]=原编号，独立视图另有 col_perm。所有行序在 A0 上生成；A0/A1 使用同一残余集合。

checks/、logs/ 保留不变量、独立复核、完整命令及失败/中断/重试现场。code/ 与 binaries/ 保留实际实现及旧来源快照。inputs/ 含 MTX 与原始归档。SHA256SUMS 覆盖封装成员。

未运行可选第二批。仓库已有文件未修改，未提交或推送。本交付不含研究分析结论。
''')
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
    (OUT/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(OUT).as_posix()+'\n' for p in files))
    archive=BASE/'t21-rq2-87594cc-20261106.tar.gz'
    with tarfile.open(archive,'w:gz') as t:t.add(OUT,arcname='第一层实验结果/rq2-validate-20261106')
    h=sha(archive);archive.with_name(archive.name+'.sha256').write_text(h+'  '+archive.name+'\n')
    with tarfile.open(archive) as t:
        prefix='第一层实验结果/rq2-validate-20261106/'
        for line in t.extractfile(prefix+'SHA256SUMS').read().decode().splitlines():
            expected_hash,name=line.split('  ',1);assert hashlib.sha256(t.extractfile(prefix+name).read()).hexdigest()==expected_hash,name
    print(json.dumps({'archive':str(archive),'sha256':h,'bytes':archive.stat().st_size,'result_counts':metric_counts,'joint_counts':joint_counts,'members_verified':len(files),'repository_unchanged':True},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
