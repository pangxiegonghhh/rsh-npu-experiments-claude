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
    inputs=acquisition();real_acquisition=run_stage.acquisition
    run_stage.acquisition=lambda:{m:{'status':'OK'} for m in MATRICES}
    expected=[s for stage in ('p0','p1','independent','p2') for s in run_stage.specs(stage)]
    run_stage.acquisition=real_acquisition
    failures=[]
    for spec in expected:
        path=OUT/'tasks'/(spec['key']+'.json')
        command=BASE/'logs/jobs'/(spec['key']+'.command.json')
        if spec['matrix'] in inputs and inputs[spec['matrix']]['status']=='OK':
            if path.exists() and command.exists() and json.loads(command.read_text()).get('returncode')==0:continue
            reason='Job incomplete; see logs/jobs/'+spec['key']+'.command.json'
            if command.exists():reason+='; '+json.dumps(json.loads(command.read_text()),ensure_ascii=False)
            failures.append(spec['key']);status='INCOMPLETE'
        else:
            d=inputs[spec['matrix']];status='SKIPPED' if spec['matrix']=='wiki-RfA' else 'INCOMPLETE'
            reason='Input unavailable: official endpoint HTTP 403; official HTTPS file-server SSL connection failed; user confirms no local cache. Details in logs/input-acquisition.json. '+d.get('error','')
        # Preserve any completed rows of an interrupted job and only add missing condition rows.
        rr,jj=missing_rows(spec,status,reason)
        present={(r['matrix'],r['member'],r['W'],str(r['tau']),r['placement'],r['d_rule'],r['diag'],r['member_params']) for r in rows}
        for r in rr:
            key=(r['matrix'],r['member'],r['W'],str(r['tau']),r['placement'],r['d_rule'],r['diag'],r['member_params'])
            if key not in present:rows.append(r)
        joint.extend(jj)
    dependency=json.loads((BASE/'logs/p2-dependencies.json').read_text())
    assert not dependency['available'],'C6 implementation must run before finalizing if dependency available'
    for matrix in MATRICES:
        for mnc in (0,1,4,16):
            spec={'kind':'c6','matrix':matrix,'member':'C6' if mnc==0 else 'C6-M','W':16,'mnc':mnc,'seed':0}
            rr,jj=missing_rows(spec,'SKIPPED','KaHyPar / PaToH unavailable; installation evidence in logs/p2-dependencies*. No substitute partitioner used.')
            rows.extend(rr);joint.extend(jj)
        for member in ('B-RSH-ref','B-Neutron-ref'):
            rows.append(dict(matrix=matrix,member=member,member_params='{}',status='SKIPPED',note='Optional T4/T2 reference not available in selected repository commit; pilot variants are separately labeled.'))
    for filename,data,fields in [('results.csv',rows,FIELDS),('joint.csv',joint,JOINT_FIELDS)]:
        with (OUT/filename).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(data)
    dump(OUT/'checks/invariants.json',{'all_recorded_checks_passed':True,'checks':checks,'D_checks':sum('membership_unchanged'in x for x in checks),'LS_checks':sum('ls_incremental_equals_full_recompute'in x for x in checks)})
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
        for m in MATRICES:f.write('| '+m+' | '+' | '.join(lookup[(m,x)]['status'] for x in members)+' |\n')
    (OUT/'logs').mkdir(exist_ok=True);shutil.copytree(BASE/'logs',OUT/'logs',dirs_exist_ok=True)
    (OUT/'code').mkdir(exist_ok=True);shutil.copytree(BASE/'scripts',OUT/'code/runner',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(REPO/'第一层工作区/T17-空白一试算脚本',OUT/'code/reference',dirs_exist_ok=True)
    shutil.copy2(REPO/'第一层工作区/RQ2验证实验方案.md',OUT/'code/RQ2验证实验方案.md')
    (OUT/'binaries').mkdir(exist_ok=True)
    for p in list((BASE/'work').glob('*.dylib'))+[BASE/'work/selfcheck/rq2_hk_bin']:shutil.copy2(p,OUT/'binaries'/p.name)
    shutil.copytree(BASE/'work/selfcheck/out',OUT/'selfcheck',dirs_exist_ok=True)
    (OUT/'inputs').mkdir(exist_ok=True)
    for m,d in inputs.items():
        if d['status']=='OK':shutil.copy2(d['mtx'],OUT/'inputs'/(m+'.mtx'))
    shutil.copy2(BASE/'inputs/arxiv.zip',OUT/'inputs/arxiv-original.zip')
    before=json.loads((BASE/'logs/repository-before.json').read_text())
    after={str(p.relative_to(REPO)):sha(p) for p in REPO.rglob('*') if p.is_file() and '.git' not in p.parts}
    integrity={'all_checked_out_files_unchanged':before==after,'files_checked':len(before),'git_status_porcelain':subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True),'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()}
    assert integrity['all_checked_out_files_unchanged'] and not integrity['git_status_porcelain'];dump(OUT/'checks/repository-integrity.json',integrity)
    metric_counts=dict(collections.Counter(r['status'] for r in rows));joint_counts=dict(collections.Counter(r['status'] for r in joint))
    manifest={'task':'T21','date_asia_shanghai':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'repository_url':'https://github.com/pangxiegonghhh/rsh-npu-experiments-claude','commit':integrity['HEAD'],'tree':'0c49766a7e2d57e72b0e4da777c19fff58207c5c','outcome':'INCOMPLETE_FIRST_BATCH_INPUTS_UNAVAILABLE','repository_unchanged':True,'pushed':False,'CPU_only':True,'matrices':json.loads((BASE/'logs/matrix-statistics.json').read_text()),'environment':json.loads((BASE/'logs/environment.json').read_text()),'expected_specs':expected,'parameters':{'row_order_computed_on':'A0','A1':'A0 + all diagonal positions, evaluation only','residual':'deg_A0 <= tau, identical for A0 and A1','D':'reference rq2lib.dstage, membership and sumU/sumGamma exact invariants','K_tile_width':16,'D_exact_matrices':['cora','dawson5','olafu'],'LS_sweeps_max':10,'LS_cand_parts':3,'LS_seeds_cora_arxiv':[0,1,2],'LS_full_control_seed':0,'LS_ties':'overlap descending then group ID ascending; candidate member current order','LS_rng':'Python random.Random, original reference movable iteration order','indep_CBM_co_pair_limit':50000000,'method_timeout_sec':7200,'worker_count':2,'independent_worker_count':1},'results_status_counts':metric_counts,'joint_status_counts':joint_counts,'job_failures':failures,'selfcheck':json.loads((BASE/'logs/selfcheck-gate.json').read_text()),'native_tableA':json.loads((BASE/'logs/port-validation.json').read_text()),'independent_reference_check':json.loads((BASE/'logs/independent-selfcheck-comparison.json').read_text()),'independent_campaign_audit':{'passed':json.loads((BASE/'logs/independent-campaign-audit.json').read_text())['passed'],'path':'logs/independent-campaign-audit.json'},'dependency_status':dependency,'code_sha256':{str(p.relative_to(OUT)):sha(p) for p in (OUT/'code').rglob('*') if p.is_file()},'binary_sha256':{p.name:sha(p) for p in (OUT/'binaries').iterdir()},'optional_second_batch':'not run; first-batch and P0/P1/P2 prioritized','development_notes':['No previous failed self-check materials reused.','Python TLS certificate-store error avoided using system curl with normal TLS verification.','Before formal LS jobs, movable-set order corrected; three one-sweep cases then exactly matched reference with declared stable group ties.','CBM native matches reference greedy-edge column permutations; legacy document standalone CBM numbers differ and the legacy script was not present; discrepancy recorded, no reference values changed.','P0 used the same native library as validated on Table A; later Python edits only added P1/independent functionality. Per-job code snapshots are captured from P1 onward.']}
    dump(OUT/'manifest.json',manifest)
    (OUT/'README.md').write_text('''# T21 CPU 结构验证交付\n\n基线 fd1fc09253b086daf394aa6e9c921faa59ae7569，包九树哈希与四文件哈希匹配。全新空目录原始自检首行 OK、退出码 0；加速版完整表 A 匹配。旧自检材料未沿用。\n\nCora、ogbn-arxiv 按 P0 → P1 → P2 执行；5 张 SuiteSparse 官方输入下载失败且用户无本地缓存，wiki-RfA 标 SKIPPED，其他四张标 INCOMPLETE。整批状态为 INCOMPLETE，不代表未测矩阵或方法通过。子条件及原因见 matrix-method-status.csv。\n\nresults.csv、joint.csv 是逐条件数据；manifest.json 记录参数、来源、代码和环境；orders/ 中 row_perm[新位置] = 原编号，独立视图另有 col_perm。checks/、logs/ 保留独立复核、D 不变量、局部搜索增量核对、命令及失败日志。inputs/ 保留原始 MTX 和 OGB 下载归档。code/ 与 binaries/ 保留实际实现。\n\n所有行序在 A0 上生成，A1 只用于评价；A0/A1 残余集合相同。D-exact 对大图按方案限于小矩阵；C6/C6-M 的依赖状态及安装日志另列。未运行可选第二批矩阵。\n\n仓库已有文件未修改，未提交或推送。本交付不含研究结论。\n''')
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
    (OUT/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(OUT).as_posix()+'\n' for p in files))
    archive=BASE/'t21-rq2-fd1fc09-20261106.tar.gz'
    with tarfile.open(archive,'w:gz') as t:t.add(OUT,arcname='第一层实验结果/rq2-validate-20261106')
    h=sha(archive);archive.with_name(archive.name+'.sha256').write_text(h+'  '+archive.name+'\n')
    with tarfile.open(archive) as t:
        prefix='第一层实验结果/rq2-validate-20261106/'
        for line in t.extractfile(prefix+'SHA256SUMS').read().decode().splitlines():
            expected_hash,name=line.split('  ',1);assert hashlib.sha256(t.extractfile(prefix+name).read()).hexdigest()==expected_hash,name
    print(json.dumps({'archive':str(archive),'sha256':h,'bytes':archive.stat().st_size,'result_counts':metric_counts,'joint_counts':joint_counts,'members_verified':len(files),'repository_unchanged':True},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
