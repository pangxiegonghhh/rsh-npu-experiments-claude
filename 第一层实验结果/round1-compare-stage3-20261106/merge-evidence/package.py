"""Package a verified merge, retaining raw evidence and immutable failures.

This is an evidence merge delivery, not a claim that all scientific conditions
passed or that optional checkpoint metric recovery has been performed.
"""
import csv
import json
import os
import shutil
import sys
import tarfile
from collections import Counter
from pathlib import Path

from merge import BASE, OUT, REMOTE, ORDERS, VIEW, HOST, sha, read, dump

csv.field_size_limit(32*2**20)

sys.path.insert(0, str(BASE/'scripts'))
from artifact_pack import source_proof, checksum_tree
from audit_results import audit

ROOT = OUT/'T22-T23-merged-20261110'
BULK = OUT/'T23-orders-merged-20261110'

def link(src, dst):
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    assert not dst.exists(), dst
    os.link(src, dst)

def write_csv(p, rows, fields=None):
    p.parent.mkdir(parents=True,exist_ok=True)
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def key(r):
    return (str(r.get('matrix','')),str(r.get('member','')),str(r.get('W') or 16),str(r.get('seed') or 0))

def archive(root):
    # Nested original SHA256SUMS are evidence too; exclude only our own list.
    sums=[(sha(p),p.relative_to(root).as_posix()) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'SHA256SUMS']
    (root/'SHA256SUMS').write_text(''.join(f'{h}  {name}\n' for h,name in sums))
    count=len(sums)
    target=BASE/'delivery'/(root.name+'.tar.gz')
    assert not target.exists()
    temporary=target.with_name(target.name+'.partial')
    assert not temporary.exists()
    with tarfile.open(temporary,'w:gz',compresslevel=6,dereference=True) as t:
        t.add(root,arcname=root.name)
    with tarfile.open(temporary) as t:
        names={m.name for m in t.getmembers() if m.isfile()}
        sums=t.extractfile(root.name+'/SHA256SUMS').read().decode().splitlines()
        expected={root.name+'/'+line.split('  ',1)[1]:line.split('  ',1)[0] for line in sums}
        assert names == set(expected)|{root.name+'/SHA256SUMS'}
        for name,digest in expected.items():
            assert not name.startswith('/') and '..' not in Path(name).parts
            assert __import__('hashlib').file_digest(t.extractfile(name),'sha256').hexdigest()==digest,name
    temporary.rename(target)
    receipt=dict(path=str(target),size=target.stat().st_size,sha256=sha(target),independently_readback_members=count)
    Path(str(target)+'.sha256').write_text(f'{receipt["sha256"]}  {target.name}\n')
    dump(Path(str(target)+'.receipt.json'),receipt)
    print('ARCHIVE',json.dumps(receipt),flush=True)
    return receipt

def main():
    assert read(OUT/'remote-verification.json')['passed']
    assert not ROOT.exists() and not BULK.exists()
    ROOT.mkdir();BULK.mkdir()
    assignment=read(BASE/'handoff/T23-split-20261109/assignment.json')
    ownership={c['case_id']:owner for owner in ['local','remote'] for c in assignment[owner+'_cases']}
    planned=read(BASE/'logs/stage3-planned-cases.json')
    cases={};hosts=[]
    for c in planned:
        cid=c['case_id'];owner=ownership.get(cid,'pre-split')
        raw=(REMOTE if owner=='remote' else BASE)/'work/stage3-cases'/cid/'record.json'
        d=read(raw);host=HOST if owner=='remote' else 'hostA-macos-arm64'
        row=dict(case_id=cid,matrix=c['matrix'],member=c['method'],W=c['W'],seed=c['seed'],split_owner=owner,
                 recorded_execution_host_id=host,raw_case_path=str(raw),raw_case_sha256=sha(raw),
                 generation_status=d['status'],host_provenance='actual raw command/case evidence; ownership alone not used to establish measurements',
                 inherited_coarse_timing_host_id='hostA-Rabbit-Linux-ARM-guest' if c['method'].endswith('-R') else '',
                 timing_note='-R order_sec may include historical Rabbit-U coarse time from host A; current local_seconds retained separately in raw case' if c['method'].endswith('-R') else 'actual recorded process timing; no cross-host pooling or timing replacement')
        cases[(c['matrix'],c['method'],str(c['W']),str(c['seed']))]=row;hosts.append(row)
    write_csv(ROOT/'case-host-ledger.csv',hosts)
    col=VIEW/'work/stage3-collected';annotated={}
    for p in col.glob('*.csv'):
        old=list(csv.DictReader(p.open()));new=[]
        for row in old:
            case=cases.get(key(row));d=dict(row)
            if case:
                for k in ['case_id','split_owner','recorded_execution_host_id','inherited_coarse_timing_host_id','timing_note']:d[k]=case[k]
            else:
                assert p.name=='status.csv' and row.get('scope')=='optional unavailable reference',(p.name,key(row))
                d.update(recorded_execution_host_id='',host_note='optional reference dependency unavailable, no execution implied')
            if p.name=='guard-counts.csv':d['guard_physical_scan_note']='saved reported count; not a claim of a fresh physical scan per row; native cache/backend evidence retained by host'
            new.append(d)
        write_csv(ROOT/p.name,new)
        check=list(csv.DictReader((ROOT/p.name).open()))
        assert len(check)==len(old) and all(all(a[k]==b[k] for k in a) for a,b in zip(old,check))
        annotated[p.name]=dict(rows=len(new),original_fields_preserved=True)
    # Exact field comparison with the remote table, after host columns are added.
    full=list(csv.DictReader((ROOT/'results.csv').open()))
    condition_key=lambda r:tuple(r[k] for k in ['matrix','member','diag','seed','W','tau','placement','d_rule','source'])
    index={condition_key(r):r for r in full};assert len(index)==len(full)==6276
    remote=list(csv.DictReader((REMOTE/'work/stage3-collected/results.csv').open()))
    assert len(remote)==488
    assert all(all(r[k]==index[condition_key(r)][k] for k in r) for r in remote)
    validation=audit(ROOT/'results.csv');dump(ROOT/'merged-arithmetic-audit.json',validation)
    proof=source_proof();dump(ROOT/'frozen-source-proof.json',proof)
    # Local imported source chain: preserve every historical receipt, audit into
    # this staging tree rather than overwrite a previous authoritative receipt.
    import source_provenance_audit
    (VIEW/'scripts').symlink_to(BASE/'scripts',target_is_directory=True)
    (VIEW/'logs/source-snapshots').symlink_to(BASE/'logs/source-snapshots',target_is_directory=True)
    # Audit local commands only: the remote chain has already been verified separately.
    source_provenance_audit.BASE=VIEW
    auditfn=source_provenance_audit.audit
    # Its local static audit also encounters remote commands in the view. Add
    # byte-preserved Linux source variants to a separate hash-indexed snapshot.
    (VIEW/'logs/source-snapshots').unlink()
    snapshots=VIEW/'logs/source-snapshots';snapshots.mkdir()
    for source_root,label in [(BASE/'logs/source-snapshots','hostA'),(REMOTE/'scripts','hostB-scripts'),(REMOTE/'reference_evidence','hostB-reference')]:
        if source_root.exists(): (snapshots/label).symlink_to(source_root,target_is_directory=True)
    # Path.rglob does not follow directory symlinks; explicit byte links keep
    # the hash index complete while leaving source trees untouched.
    for source_root in [BASE/'logs/source-snapshots',REMOTE/'scripts',REMOTE/'reference_evidence']:
        for p in source_root.rglob('*'):
            if p.is_file() and p.suffix in ['.py','.cpp','.c','.ini','.plist']:
                q=snapshots/(sha(p)+p.suffix)
                if not q.exists():os.link(p,q)
    versions=auditfn();assert versions['passed']
    link(VIEW/'logs/stage3-source-provenance-audit.json',ROOT/'combined-source-chain-audit.json')
    # Actual orders, including frozen reuse references, in a separate bulk package.
    entries=[];seen={}
    for kind in ['new','reused']:
        orders=read(col/(kind+'-orders.json'))
        for i,x in enumerate(orders):
            p=Path(x['path']);digest=sha(p);assert digest==x['sha256'],p
            if digest not in seen:
                destination=Path('orders')/(digest+'.json');link(p,BULK/destination);seen[digest]=str(destination)
            entries.append(dict(x,kind=kind,package_path=seen[digest],size=p.stat().st_size,sha256=digest))
    dump(ROOT/'orders-manifest.json',dict(new_references=269,reused_references=117,unique_files=len(seen),files=entries,bulk_package=BULK.name+'.tar.gz'))
    link(ROOT/'orders-manifest.json',BULK/'orders-manifest.json')
    # Retain raw completed-sweep vectors separately, without recomputing LS/D.
    checkpoints=[]
    for root,host in [(BASE,'hostA-macos-arm64'),(REMOTE,HOST)]:
        for p in (root/'work/post-e').glob('stage3-*/last-completed-sweep.checkpoint.json'):
            rel=Path('checkpoints')/host/p.parent.name/p.name;link(p,BULK/rel)
            checkpoints.append(dict(host=host,source=str(p),package_path=str(rel),sha256=sha(p),size=p.stat().st_size))
    dump(ROOT/'checkpoints-manifest.json',checkpoints)
    # Entire returned small result tree, original bytes and Linux ELF included.
    # These executables are evidence only and were never loaded on this Mac.
    for p in REMOTE.rglob('*'):
        if p.is_file():link(p,ROOT/'raw/hostB'/p.relative_to(REMOTE))
    for n in ['stage3-cases','stage3-evaluations','stage3-diagnostics','stage3-independent','stage3-partial-post','post-e','stage3-post-catalog']:
        for p in (BASE/'work'/n).rglob('*'):
            if p.is_file() and p.name.endswith('.json') and not p.name.endswith(('order.json','checkpoint.json')):
                link(p,ROOT/'raw/hostA/work'/n/p.relative_to(BASE/'work'/n))
    for p in (BASE/'logs').rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(BASE/'logs')
        if len(rel.parts)>1 and rel.parts[0] not in ['source-snapshots','layout-context-backends','cpu-slot-starts','memory-guards','reboot-preparation-20261109T092448Z','reboot-recovery-20261109T0952Z']:continue
        if p.suffix in ['.json','.log','.stdout','.stderr','.txt','.md','.py','.c','.cpp','.diff']:
            link(p,ROOT/'raw/hostA/logs'/rel)
    for p in (BASE/'scripts').rglob('*'):
        if p.is_file() and p.suffix in ['.py','.cpp','.c','.ini','.plist']:link(p,ROOT/'code/hostA'/p.relative_to(BASE/'scripts'))
    for p in (BASE/'work').glob('*.dylib'):link(p,ROOT/'runtime/hostA'/p.name)
    for n in ['rq3-validate-20261106','round1-compare-20261106']:
        archive_path=BASE/'delivery'/(n+'.tar.gz');receipt=read(BASE/'delivery'/(n+'.receipt.json'))
        assert sha(archive_path)==receipt['sha256'];link(archive_path,ROOT/'sealed-first-deliveries'/archive_path.name)
        link(BASE/'delivery'/(n+'.receipt.json'),ROOT/'sealed-first-deliveries'/(n+'.receipt.json'))
    for n in ['archive-receipt.json','remote-verification.json','path-projections.json','retired-waiters.json','merge.py','package.py','task_plan.md','notes.md']:
        target=ROOT/'merge-evidence'/n;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(OUT/n,target)
    coverage=read(OUT/'coverage.json');dump(ROOT/'coverage.json',coverage)
    counts=Counter(r['status'] for r in full)
    manifest=dict(scope='T22 sealed archive + T23 sealed stages1-2 archive + host-aware stage3 evidence merge; no scientific rerun',
                  source_repository=proof,coverage=coverage,result_row_counts=dict(counts),remote_rows=488,
                  remote_row_counts={'OK':200,'INCOMPLETE':288},all_remote_original_table_fields_preserved=True,
                  annotated_tables=annotated,hosts={
                      'hostA-macos-arm64':{'platform':'macOS15.2 arm64','cpu':'Apple M1 Pro','memory_GiB':16,'python':'3.12.10','timing':'actual original records; external Rabbit Linux ARM guest separate'},
                      HOST:{k:read(REMOTE/'logs/remote-port-preparation.json')[k] for k in ['platform','machine','python','numpy','scipy']}},
                  raw_hostB_root='raw/hostB',raw_hostA_root='raw/hostA',orders_bulk=BULK.name+'.tar.gz',
                  no_failed_status_promoted=True,checkpoints_recomputed=False,LS_or_D_rerun=False,
                  formal_stage3_seal='not performed by this evidence merge; original formal builder guard/checkpoint recovery closure is distinct',
                  git_commit_or_push=False,automation='t22-t23 deleted',waiters='two idle local waiters retired; no scientific process interrupted')
    dump(ROOT/'manifest.json',manifest)
    (ROOT/'README.md').write_text('''# T22 / T23 双主机合并交付（2026-11-10）

T22 与 T23 阶段1–2的原始封存包位于 sealed-first-deliveries/，字节和 SHA 不变。
本目录 results.csv、status.csv 等为 T23 阶段3的独立合并导出；不覆盖原始表。
409例全部有真实终止记录：320 OK、48 INCOMPLETE、41 SKIPPED；另列6个可选参照 SKIPPED。
6276行正式条件；远端20例488行（200 OK、288 INCOMPLETE），原表全部字段逐项保持。
整例状态与生成阶段状态不同，不能把生成 OK 或“终止”视为整例通过。

## 文件与核验

- results.csv / status.csv / diag.csv / groups.csv / guard-counts.csv / post-E.csv：合并表与主机标签。
- case-host-ledger.csv：409例的实际原件、SHA、主机与历史 Rabbit 粗排计时来源。
- raw/hostA/ 与 raw/hostB/：原始科学记录、日志、源码和平台证据分开保留。
- merge-evidence/remote-verification.json：263冻结文件、输入哈希、11个新WSL门禁、源码链、ELF及19行序校验。
- combined-source-chain-audit.json：按实际命令SHA核验入口与静态本地导入源码，不执行返还的程序。
- merged-arithmetic-audit.json：所有OK行的算术、固定成员U/T和比值不变量核验。
- orders-manifest.json / checkpoints-manifest.json：大文件位于单独的 T23-orders-merged-20261110.tar.gz。
- SHA256SUMS：本包所有文件；外部同名 .sha256 校验整个 tar.gz。

## 口径与限制

hostB为Windows/WSL2 x86_64、AMD Ryzen7 5800H，Python3.12.3、NumPy2.4.4、SciPy1.17.1。
hostA为Mac M1 Pro 16GiB、macOS15.2 arm64、Python3.12.10。实际版本原件分别保留。
Linux RSS仅作KiB→MiB移植，5处源码反向还原AST一致，ELF按构建/加载SHA独立核验。
不同主机耗时不混合平均或互换。-R的历史Rabbit-U粗排成本来自hostA，原local_seconds另见记录。
guard计数是保存的条件报告，可能继承缓存，不按行数宣称独立物理扫描；未增加Linux生产者白名单。
Reddit C8-METIS τ53超时、τ153重启中断和products C6-HP exit -9保持INCOMPLETE。
远端C3-A原生成超时保持INCOMPLETE，未产生最终行序，未用其他方法行序代替。
原完成轮次检查点保留完整向量，但本次合并不重跑LS、D或检查点评价。
本包完成数据合并与证据核验，不声称另一个正式阶段3封存流程的所有回收步骤已闭合。
无NPU、无提交或推送，未写分析结论。定时任务已删除；两个空闲等待进程已行政停止。
''')
    bulk_receipt=archive(BULK)
    dump(ROOT/'orders-package-receipt.json',bulk_receipt)
    result_receipt=archive(ROOT)
    dump(OUT/'merge-receipt.json',dict(passed=True,coverage=coverage,remote_original_rows_verified=488,
         results=result_receipt,orders=bulk_receipt,automation_deleted=True,raw_results_unchanged=True,
         scope='verified local evidence merge, not a claim of all scientific conditions PASS'))

if __name__=='__main__':main()
