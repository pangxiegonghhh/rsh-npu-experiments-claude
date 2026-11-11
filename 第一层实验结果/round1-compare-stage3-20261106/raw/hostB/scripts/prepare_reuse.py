from __future__ import annotations
import csv,datetime,hashlib,json,shutil,tarfile,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];REPO=BASE/'repo'
ARCHIVE=Path('/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/第一层工作区/RQ2实验数据/t21-rq2-87594cc-20261106.tar.gz')
PREFIX='第一层实验结果/rq2-validate-20261106/'
def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def main():
    start=time.perf_counter();assert ARCHIVE.stat().st_size==697813699
    checksum=sha(ARCHIVE);assert checksum=='2b824ec698df32a9a2027fc3b896c5e68fb3e5982cd696c7ea6c9a1cae6b719a'
    lists={}
    for task in ('T22','T23'):
        with (REPO/f'第一层工作区/{task}派发/orders-index.csv').open(newline='')as f:lists[task]=list(csv.DictReader(f))
    wanted={'manifest.json','results.csv','joint.csv','SHA256SUMS'};index={}
    for task,rows in lists.items():
        for row in rows:
            if not row['sha256']:continue
            path=row['t21_path']if task=='T22'else row['path']
            if task=='T23'and row['source']!='T21 完整归档':continue
            wanted.add(path);assert path not in index or index[path]==row['sha256'];index[path]=row['sha256']
    for name in ('cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1'):wanted.add('inputs/'+name+'.mtx')
    target=BASE/'inputs/t21';target.mkdir(parents=True,exist_ok=True);found=set()
    with tarfile.open(ARCHIVE,mode='r|gz')as tar:
        for item in tar:
            if not item.isfile()or not item.name.startswith(PREFIX):continue
            rel=item.name[len(PREFIX):]
            if rel not in wanted:continue
            path=target/rel;assert path.resolve().is_relative_to(target.resolve());path.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(item)as src,path.open('wb')as dst:shutil.copyfileobj(src,dst,1<<20)
            found.add(rel)
    assert found==wanted,sorted(wanted-found)
    sealed={line.split('  ',1)[1]:line.split('  ',1)[0]for line in (target/'SHA256SUMS').read_text().splitlines()}
    manifests=[]
    for task,rows in lists.items():
        for row in rows:
            if not row['sha256']:continue
            rel=row['t21_path']if task=='T22'else row['path']
            if task=='T23'and row['source']!='T21 完整归档':
                path=REPO/'第一层实验结果/rq2-c6align-20261106'/rel;origin='repository alignment supplement'
            else:
                path=target/rel;origin='T21 archive';assert sealed[rel]==row['sha256']
            actual=sha(path);assert actual==row['sha256'],(task,rel)
            data=json.loads(path.read_text());order=data['row_perm'];assert len(order)==len(set(order))and min(order)==0 and max(order)==len(order)-1
            manifests.append({'task':task,**row,'runtime_path':str(path),'verified_sha256':actual,'origin':origin})
    parent=json.loads((target/'manifest.json').read_text());inputs=[]
    for item in parent['matrices']:
        path=target/'inputs'/(item['matrix']+'.mtx');assert sha(path)==item['input_mtx_sha256']
        inputs.append({**item,'parent_runtime_path':item['input_path'],'input_path':str(path)})
    (BASE/'logs/reused-orders.json').write_text(json.dumps(manifests,ensure_ascii=False,indent=2))
    (BASE/'logs/first-batch-matrices.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2))
    record={'passed':True,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(ARCHIVE),'archive_sha256':checksum,
      'archive_bytes':ARCHIVE.stat().st_size,'archive_files_extracted':len(found),'T22_verified_reuse':sum(x['task']=='T22'for x in manifests),
      'T23_verified_reuse':sum(x['task']=='T23'for x in manifests),'T22_new_LSfull_required':2,'elapsed_sec':time.perf_counter()-start}
    assert record['T22_verified_reuse']==97 and record['T23_verified_reuse']==144
    (BASE/'logs/input-reuse-gate.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));print(json.dumps(record,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
