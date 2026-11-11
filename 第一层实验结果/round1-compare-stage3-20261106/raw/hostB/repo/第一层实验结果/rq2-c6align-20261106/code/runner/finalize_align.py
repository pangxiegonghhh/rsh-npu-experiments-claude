from __future__ import annotations
import collections,csv,datetime,hashlib,json,re,shutil,subprocess,sys,tarfile
from pathlib import Path
sys.dont_write_bytecode=True
from align_context import BASE,OLD,PARENT,OUT,PROTOCOL,dump,sha,assert_runtime
from check_align_gates import gate3
from audit_align import audit
def csv_header(path:Path)->list[str]:
    with path.open(newline='')as f:return next(csv.reader(f))
def main()->None:
    assert_runtime();assert (BASE/'logs/pipeline.stdout.log').read_text().endswith('MAIN_FINISHED\n')
    assert json.loads((OUT/'checks/gate1-failed-model-replay.json').read_text())['passed']
    assert json.loads((OUT/'checks/gate2-cora-noop.json').read_text())['passed']
    third=gate3();records=json.loads((BASE/'logs/main-records.json').read_text());assert len(records)==4
    fields=csv_header(PARENT/'results.csv');joint_fields=csv_header(PARENT/'joint.csv');assert len(fields)==26 and len(joint_fields)==32
    rows=[];joint=[];cases=[]
    for mnc in (0,1,4,16):
        member='C6'if mnc==0 else'C6-M';key=f'c6__pattern1__{member}__W16__{mnc}';record=next(r for r in records if r['case']==key)
        tracepath=OUT/'checks'/(key+'-bisections.json');trace=json.loads(tracepath.read_text())if tracepath.exists()else{'calls':[],'align_repairs':[]}
        status='OK'if record['returncode']==0 else'INCOMPLETE';repair=trace.get('align_repairs',[])
        summary={'rule':'min weighted-cut increase per single-vertex move, oversized->undersized block, ties smallest local index; cap |d|<=W//2','cap':8,
          'calls_repaired':len(repair),'vertices_moved':sum(len(x['moved_global_vertices'])for x in repair),
          'max_abs_d':max((abs(x['actual_sizes'][0]-x['targets'][0])for x in trace['calls']),default=0),
          'weighted_cut_delta_total':sum(x['weighted_cut_after']-x['weighted_cut_before']for x in repair)}
        partition_sec=trace.get('elapsed_sec')
        if status=='OK':
            task=json.loads((OUT/'tasks'/(key+'.json')).read_text());assert len(task['rows'])==len(task['joint'])==16
            params=json.loads(task['rows'][0]['member_params']);assert params['alignment_repair']==summary
            assert trace['status']=='OK'and len(trace['calls'])==1202
            for call in trace['calls']:
                final=call.get('align_repair',{}).get('final_sizes',call['actual_sizes']);assert final==call['targets']
                if 'align_repair'in call:assert abs(call['align_repair']['d'])<=8
            partition_sec=params['partition_sec'];rows.extend(task['rows']);joint.extend(task['joint'])
        else:
            reason='INCOMPLETE; returncode='+str(record['returncode'])+'; timeout='+str(record.get('timed_out',False))+'; trace=checks/'+tracepath.name+'; stderr=logs/jobs/main/'+key+'.stderr.log'
            if trace['calls']:reason+='; '+trace['calls'][-1].get('failure','')
            params={**record['spec'],'alignment_repair':summary,'trace':'checks/'+tracepath.name}
            for tau in ('none',2,3):
                for placement,rule in ([('none','own'),('none','D-greedy')]if tau=='none'else[('inplace','own'),('tail','own'),('tail','D-greedy')]):
                    for diag in ('A0','A1'):
                        row=dict(matrix='pattern1',diag=diag,member=member,member_params=json.dumps(params,ensure_ascii=False),W=16,tau=tau,placement=placement,d_rule=rule,status=status,note=reason)
                        rows.append(row);joint.append({**row,'start':'column-net recursive bisection','mnc':mnc,'seed':0})
        cases.append({'case':key,'mnc':mnc,'status':status,'bisection_calls':len(trace['calls']),**summary,'partition_sec':partition_sec,'wall_sec':record['elapsed_sec'],'returncode':record['returncode']})
    assert len(rows)==len(joint)==64
    keys=lambda r:(json.loads(r['member_params'])['mnc'],r['diag'],str(r['W']),str(r['tau']),r['placement'],r['d_rule'])
    assert len({keys(r)for r in rows})==64 and {keys(r)for r in rows}=={keys(r)for r in joint}
    independent=audit(rows)
    for name,data,header in [('results-c6align.csv',rows,fields),('joint-c6align.csv',joint,joint_fields)]:
        with (OUT/name).open('w',newline='')as f:writer=csv.DictWriter(f,fieldnames=header,extrasaction='ignore');writer.writeheader();writer.writerows(data)
    dump(OUT/'checks/case-summary.json',{'cases':cases})
    before=json.loads((BASE/'logs/original-t21-before.json').read_text())
    for name,expected in before['original_output_hashes'].items():assert sha(PARENT/name)==expected,name
    assert sha(Path(before['original_archive']))==before['original_archive_sha256']
    for name,expected in before['original_runtime_hashes'].items():assert sha(Path(name))==expected,name
    preserved={'passed':True,'parent_files_checked':len(before['original_output_hashes']),'parent_archive_sha256':before['original_archive_sha256'],'parent_runtime_unchanged':True}
    dump(OUT/'checks/original-t21-preserved.json',preserved)
    repo=BASE/'repo';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    applied=json.loads((BASE/'logs/package-application.json').read_text());assert git('rev-parse','HEAD')==applied['before_commit']
    assert git('write-tree')=='ca3af5408b13a8ec9a424452649ebe943a902d19'and not git('diff','--name-only')
    for item in applied['after_files']:assert sha(repo/item['path'])==item['sha256'],item['path']
    dump(OUT/'checks/repository-state.json',{'passed':True,'HEAD':git('rev-parse','HEAD'),'index_tree':git('write-tree'),'commits_created':0,'pushed':False,'git_status':git('status','--porcelain')})
    order_bytes=sum(p.stat().st_size for p in (OUT/'orders').glob('*.json'));assert order_bytes<=20*1024*1024
    (OUT/'code/runner').mkdir(parents=True,exist_ok=True)
    for p in (BASE/'scripts').iterdir():
        if p.is_file():shutil.copy2(p,OUT/'code/runner'/p.name)
    shutil.copytree(PROTOCOL,OUT/'code/package15-protocol',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(BASE/'package/rsh_pkg15',OUT/'code/package15-application',dirs_exist_ok=True)
    shutil.copytree(BASE/'logs',OUT/'logs',dirs_exist_ok=True)
    parentcopy=OUT/'checks/parent-failed-models';parentcopy.mkdir(exist_ok=True)
    for p in (PARENT/'checks').glob('c6__pattern1__*'):shutil.copy2(p,parentcopy/p.name)
    counts=dict(collections.Counter(r['status']for r in rows));env=json.loads((BASE/'logs/environment.json').read_text())
    manifest={'task':'T21 package15 alignment supplement','date_asia_shanghai':'2026-11-06','original_T21_preserved':preserved,
      'repository_baseline_commit':applied['before_commit'],'applied_index_tree':applied['after_index_tree'],'commits_created':0,'pushed':False,
      'c6_sha256':sha(BASE/'scripts/c6.py'),'campaign_sha256':sha(BASE/'scripts/campaign.py'),'environment':env,'cases':cases,
      'gates':{'gate1':True,'gate2':True,'gate3':third['passed']},'independent_metrics':{'passed':independent['passed'],'conditions_checked':independent['metric_conditions_checked']},
      'parameters':{'W':16,'mnc':[0,1,4,16],'seed':0,'epsilon':0.0,'alignment_repair_cap':8,'timeout_sec':7200,'max_parallel_cases':2},
      'row_counts':{'results':64,'joint':64},'status_counts':counts,'orders_bytes':order_bytes,
      'code_sha256':{str(p.relative_to(OUT)):sha(p)for p in (OUT/'code').rglob('*')if p.is_file()}}
    dump(OUT/'manifest.json',manifest)
    lines=['# T21 包十五：C6 对齐修补补跑','',
      '独立副本应用后索引树为 ca3af5408b13a8ec9a424452649ebe943a902d19；HEAD 保持 c6da5f817180bf800364b9a6a762f8341a32b4d8。未提交、未推送。',
      '',f'门 1：4 个 MATCH。门 2：两例各 169 次调用、16 个指标条件和 6 个行序逐位相同，修补未触发。门 3：'+('四例前缀与旧失败层修补均复现。'if third['passed']else'**存在未复现的用例，见 checks/gate3-pattern1-prefix.json。**'),'',
      '| 用例 | 状态 | 二分调用 | 修补次数 | 挪动点数 | 最大 \\|d\\| | 加权割变化合计 | 划分秒 |',
      '|---|---|---:|---:|---:|---:|---:|---:|']
    for c in cases:lines.append('| '+' | '.join(str(x)for x in [c['case'],c['status'],c['bisection_calls'],c['calls_repaired'],c['vertices_moved'],c['max_abs_d'],c['weighted_cut_delta_total'],round(c['partition_sec'],6)if c['partition_sec']is not None else'未完成'])+' |')
    lines+=['',f'CSV 各 64 行，表头分别与 T21 的 26 / 32 列完全相同。独立原始矩阵复算 {independent["metric_conditions_checked"]} 个有效条件；D 阶段成员、残余顺序、ΣU 和 ΣΓ 均核验。行序总计 {order_bytes} 字节，全部随包交回。','',
      '软件环境与 T21 一致：KaHyPar 1.3.7、模块与配置哈希均匹配，种子 0、ε=0；campaign.py 原样复用，仅替换 c6.py。新调用脚本将输出重定向到本目录，实际运行路径、命令和哈希见 logs/。',
      '', '启动准备中曾漏复制辅助 HK 程序，导入 rq2lib 时链接失败，尚未开始 Cora 计算；补齐与 T21 字节相同的工作目录辅助文件后，实际门 2 核对通过。原始启动错误保存在 logs/setup-import-failure/，修复说明见 logs/setup-import-repair.json。四个主用例均仅执行一次，不重试、不改参数。',
      '',f'原 T21 交付 {preserved["parent_files_checked"]} 个文件、原完整归档及所用原运行文件的 SHA-256 全部保持不变。原归档 SHA-256：{preserved["parent_archive_sha256"]}。',
      '', '本包不含研究分析结论。results-c6align.csv / joint-c6align.csv 是新结果，未合并或覆盖 T21 原表。']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n')
    files=sorted(p for p in OUT.rglob('*')if p.is_file()and p.name!='SHA256SUMS')
    (OUT/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(OUT).as_posix()+'\n'for p in files))
    archive=BASE/'t21-c6align-pkg15-20261106.tar.gz';prefix='第一层实验结果/rq2-c6align-20261106'
    with tarfile.open(archive,'w:gz')as tar:tar.add(OUT,arcname=prefix)
    checksum=sha(archive);archive.with_name(archive.name+'.sha256').write_text(checksum+'  '+archive.name+'\n')
    with tarfile.open(archive)as tar:
        for line in tar.extractfile(prefix+'/SHA256SUMS').read().decode().splitlines():
            expected,name=line.split('  ',1);assert hashlib.sha256(tar.extractfile(prefix+'/'+name).read()).hexdigest()==expected,name
    receipt={'archive':str(archive),'sha256':checksum,'bytes':archive.stat().st_size,'members_verified':len(files),'cases':cases,'gates':manifest['gates'],'status_counts':counts,'parent_preserved':True,'commits_created':0,'pushed':False}
    dump(BASE/'delivery-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
