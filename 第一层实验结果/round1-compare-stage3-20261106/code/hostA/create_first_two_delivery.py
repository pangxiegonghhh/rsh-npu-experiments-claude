"""Transfer sealed T22 and T23 stages1-2 plus their complete order artifacts."""
import csv,hashlib,json,pathlib,shutil,tarfile,time
from first_group_supplement import rows as group_rows
BASE=pathlib.Path(__file__).resolve().parents[1]
DEL=BASE/'delivery'
def sha(p):
 with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);assert sha(src)==sha(dst)
def csvout(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def verify_sealed(name,expected):
 p=DEL/(name+'.tar.gz');assert sha(p)==expected
 with tarfile.open(p,'r:gz') as t:
  members={m.name:m for m in t.getmembers() if m.isfile()}
  sums=next(k for k in members if k.endswith('/SHA256SUMS'));prefix=sums.rsplit('/',1)[0]+'/'
  entries={prefix+line.split('  ',1)[1]:line.split('  ',1)[0] for line in t.extractfile(members[sums]).read().decode().splitlines()}
  assert set(members)==set(entries)|{sums}
  for path,h in entries.items():
   with t.extractfile(members[path]) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==h,path
 return dict(original_archive_sha256=expected,archive_files_checked=len(members),checksummed_files=len(entries))
def build(name,label,expected):
 original=verify_sealed(name,expected);root=DEL/(label+'-complete-20261109-v2');assert not root.exists();root.mkdir()
 formal=DEL/'第一层实验结果'/name;manifest=json.loads((formal/'manifest.json').read_text());orders=json.loads((formal/'orders-manifest.json').read_text())
 for p in DEL.glob(name+'.*'):
  if p.is_file():copy(p,root/'sealed-original'/p.name)
 order_entries=[]
 for i,item in enumerate(orders['files']):
  p=pathlib.Path(item.get('local_path') or item['path']);assert sha(p)==item['sha256'];dst=root/'orders/new'/p.name;copy(p,dst)
  order_entries.append(dict(item,transfer_path=dst.relative_to(root).as_posix(),transfer_role='actual originally local-only order; formal archive unchanged'))
 reused=[]
 indexed=[r for r in json.loads((BASE/'logs/reused-orders.json').read_text()) if r['task']==('T22' if label=='T22' else 'T23')]
 assert len(indexed)==(97 if label=='T22' else 144)
 reuse_items=manifest['reused_orders'] if label=='T22' else indexed
 assert {r['sha256'] for r in indexed}<={r['sha256'] for r in reuse_items}
 assert {r['sha256'] for r in manifest['reused_orders']}<={r['sha256'] for r in reuse_items}
 for i,item in enumerate(reuse_items):
  p=pathlib.Path(item['runtime_path']);assert sha(p)==item['sha256'];dst=root/'orders/reused'/(str(i).zfill(4)+'__'+item['sha256']+'.json');copy(p,dst);reused.append(dict(item,transfer_path=dst.relative_to(root).as_posix()))
 dump(root/'orders-transfer-index.json',dict(new=order_entries,reused=reused,formal_original_order_manifest='sealed-original/'+name+'.tar.gz',note='Transfer paths are relative to this outer bundle. Original historical paths/metadata are retained unchanged. No new scientific order was calculated.'))
 task='T22' if label=='T22' else 'T23'
 for rel in [f'第一层工作区/{task}派发/说明.md',f'第一层工作区/{task}派发/orders-index.csv','第一层工作区/RQ3验证实验方案.md' if task=='T22' else '第一层工作区/首轮候选比较实验方案.md']:
  copy(BASE/'repo'/rel,root/'reference'/pathlib.Path(rel))
 if label=='T23-stages1-2':
  sup=root/'supplements';sup.mkdir();g=group_rows();csvout(sup/'first-delivery-group-diagnostics.csv',g)
  for row in g:
   p=pathlib.Path(row['source_record']);assert sha(p)==row['source_record_sha256'];copy(p,sup/'evidence'/row['source_record_sha256']/p.name)
  for n in ['first_group_supplement.py','group_metadata.py']:copy(BASE/'scripts'/n,sup/'code'/n)
  inherited=[]
  for r in json.loads((BASE/'logs/reused-pls-invariants.json').read_text())['checks']:
   if r['member'] in ['C9-Gorder','rsh-α0'] and r['lam']==0:
    inherited.append(dict(matrix=r['matrix'],member='B1' if r['member']=='rsh-α0' else r['member'],W=16,tau=r['tau'],seed=0,first_delivery_reuse_execution_post_sec=0,inherited_T21_post_computation_seconds=r['T21_order_sec'],source_path=r['source_path'],source_sha256=r['source_sha256'],fresh_UG_verified=True))
  assert len(inherited)==12;csvout(sup/'first-delivery-reused-post-costs.csv',inherited);copy(BASE/'logs/reused-pls-invariants.json',sup/'reused-pls-invariants.json')
  memory=json.loads((DEL/(name+'.post-memory-supplement.json')).read_text());assert memory['passed'] and memory['supplement_rows']==896
  text='补充表含896条post-E原始进程峰值、70条已保存分组元数据及12条T21原始post耗时引用。复用本轮post_sec=0与历史计算用时分列；峰值是本轮验证进程（可能含LS验证）峰值，不是T21历史峰值。'
 else:text='环境补充及独立审计随封存原件一并提供。'
 result_rows=sum(1 for _ in csv.DictReader((formal/'results.csv').open()))
 audit=dict(package_scope=label,formal_original=original,result_rows=result_rows,new_order_files=len(order_entries),new_order_bytes=sum(x['size'] for x in order_entries),reused_order_files=len(reused),stage3_included=False,science_rerun=False,sealed_original_unchanged=True)
 dump(root/'TRANSFER-MANIFEST.json',audit)
 (root/'README.md').write_text('# '+label+' 完整交接包\n\n本包只含'+('T22 RQ3验证' if label=='T22' else 'T23阶段1–2第一批矩阵')+'，与阶段3独立。\n\nsealed-original/ 内保留正式封存归档、原SHA256和收据；其字节未修改。解开其中tar.gz即可取得results、各项比较/诊断表、状态表、manifest、README、原始日志、自检和源码/运行库。\n\norders/ 额外提供此前受50MiB政策限制而留在本机的所有实际新行序，并附复用行序原件；orders-transfer-index.json给出相对路径、来源及原SHA。为本次完整传输额外打包，不改变原正式归档的local-only清单或历史表述。原记录中的绝对路径是历史来源，搬到新机器时按此清单定位。\n\n'+text+'\n\n本次没有重跑实验、没有写分析结论、没有提交或推送。阶段3不在本包内。\n\nSHA256SUMS覆盖本外包全部文件（不含清单本身）。主结果表行数：'+str(result_rows)+'；新行序：'+str(len(order_entries))+'；复用行序：'+str(len(reused))+'。\n')
 files={p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}
 (root/'SHA256SUMS').write_text(''.join(h+'  '+rel+'\n' for rel,h in sorted(files.items())))
 files['SHA256SUMS']=sha(root/'SHA256SUMS');out=DEL/(root.name+'.tar.gz');assert not out.exists();tmp=pathlib.Path(str(out)+'.part')
 with tarfile.open(tmp,'w:gz',compresslevel=1) as t:
  for rel in sorted(files):t.add(root/rel,arcname=root.name+'/'+rel,recursive=False)
 with tarfile.open(tmp,'r:gz') as t:
  members=t.getmembers();assert len(members)==len(files)
  for m in members:
   assert m.isfile();rel=m.name[len(root.name)+1:]
   with t.extractfile(m) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==files[rel],rel
 tmp.rename(out);h=sha(out);pathlib.Path(str(out)+'.sha256').write_text(h+'  '+out.name+'\n');assert sha(DEL/(name+'.tar.gz'))==expected
 receipt=dict(passed=True,path=str(out),sha256=h,bytes=out.stat().st_size,archive_files_independently_checked=len(files),**audit);dump(DEL/(root.name+'.receipt.json'),receipt);print(json.dumps(receipt,ensure_ascii=False),flush=True)
if __name__=='__main__':
 build('rq3-validate-20261106','T22','9b77737f0e074666e78b915bc34b6b51b66fe005889de783df7f35d13d8cbca3')
 build('round1-compare-20261106','T23-stages1-2','2493fceb5c7ed4b2747fa1c38d912f7321b5aa9bd29949f85cc1c835177fe196')
