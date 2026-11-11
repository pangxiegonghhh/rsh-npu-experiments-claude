import csv,datetime,hashlib,json,os,platform,shutil,subprocess,tarfile
from pathlib import Path
from native import BASE
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for data in iter(lambda:f.read(2**20),b''):h.update(data)
 return h.hexdigest()
def dump(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2))
def source_proof():
 git=lambda *args:subprocess.check_output(['git','-C',str(BASE/'repo'),*args],text=True).strip()
 original=json.loads((BASE/'logs/repository-before.json').read_text());changed=[name for name,h in original.items() if not (BASE/'repo'/name).exists() or sha(BASE/'repo'/name)!=h];status=git('status','--porcelain=v1');assert not changed and not status,(changed,status);return dict(commit=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),branch=git('branch','--show-current'),status=status,verified_original_files=len(original),all_original_sha256_unchanged=True,before_manifest=str(BASE/'logs/repository-before.json'),before_manifest_sha256=sha(BASE/'logs/repository-before.json'))
def checksum_tree(root):
 rows=[]
 for p in sorted(root.rglob('*')):
  if p.is_file() and p.name!='SHA256SUMS':rows.append((sha(p),p.relative_to(root).as_posix()))
 (root/'SHA256SUMS').write_text(''.join(f'{h}  {name}\n' for h,name in rows));return len(rows)
def seal(root,name):
 checksum_tree(root);archive=BASE/'delivery'/(name+'.tar.gz')
 assert not archive.exists(),'sealed archive already exists'
 temp=archive.with_name(archive.name+'.part');assert not temp.exists(),'previous partial archive retained; inspect before retry'
 with tarfile.open(temp,'w:gz',compresslevel=6) as t:t.add(root,arcname='第一层实验结果/'+name)
 prefix='第一层实验结果/'+name+'/';checked=0
 with tarfile.open(temp,'r:gz') as t:
  lines=t.extractfile(prefix+'SHA256SUMS').read().decode().splitlines()
  expected={line.split('  ',1)[1]:line.split('  ',1)[0] for line in lines}
  actual={m.name[len(prefix):] for m in t.getmembers() if m.isfile() and m.name!=prefix+'SHA256SUMS'};assert actual==set(expected)
  for rel,h in expected.items():
   f=t.extractfile(prefix+rel);dig=hashlib.sha256()
   for data in iter(lambda:f.read(2**20),b''):dig.update(data)
   assert dig.hexdigest()==h,rel;checked+=1
 temp.rename(archive);h=sha(archive);Path(str(archive)+'.sha256').write_text(f'{h}  {archive.name}\n');return dict(path=str(archive),sha256=h,size=archive.stat().st_size,archive_members_independently_checked=checked)
def install_orders(root,name,orders):
 entries=[];unique={}
 for r in orders:
  p=Path(r['path']);h=sha(p)
  if r.get('sha256'):assert h==r['sha256'],p
  key=str(p.resolve())
  if key in unique:continue
  entry=dict(r,sha256=h,size=p.stat().st_size);entries.append(entry);unique[key]=entry
 total=sum(e['size'] for e in entries);local_only=total>50*2**20;dest=BASE/'local-orders'/name if local_only else root/'orders';dest.mkdir(parents=True,exist_ok=True)
 for i,e in enumerate(entries):
  label=e.get('member','order').replace('/','_').replace('α','alpha').replace(' ','_');fn=f"{i:04d}__{e.get('matrix','matrix')}__{label}__{e['sha256'][:12]}.json";p=dest/fn
  if p.exists():assert sha(p)==e['sha256']
  else:shutil.copyfile(e['path'],p)
  e.update(local_path=str(p),storage='local-only: over 50MiB' if local_only else 'archive',archive_path=None if local_only else 'orders/'+fn)
 (root/'orders').mkdir(exist_ok=True);dump(root/'orders-manifest.json',dict(local_only=local_only,total_bytes=total,file_count=len(entries),files=entries))
 if local_only:(root/'orders/README.md').write_text(f'新行序合计 {total} B，超过方案的 50 MiB 阈值，全部保留在本地：\n\n{dest}\n\n逐文件路径、大小与 SHA-256 见 ../orders-manifest.json。复用行序见 manifest.json。\n')
 return dict(file_count=len(entries),total_bytes=total,local_only=local_only,local_directory=str(dest),index_sha256=sha(root/'orders-manifest.json'))
def install_sources(root):
 dest=root/'code';dest.mkdir(exist_ok=True)
 entries=[]
 for p in sorted((BASE/'scripts').rglob('*')):
  if p.is_file() and p.suffix in ['.py','.cpp','.c','.ini','.plist']:
   rel=p.relative_to(BASE/'scripts');q=dest/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);entries.append(dict(path='code/'+rel.as_posix(),sha256=sha(q)))
 runtime=root/'runtime';runtime.mkdir(exist_ok=True)
 for p in sorted((BASE/'work').glob('*.dylib')):
  shutil.copyfile(p,runtime/p.name);entries.append(dict(path='runtime/'+p.name,sha256=sha(p)))
 p=BASE/'work/t21/librq2-v8.dylib'
 if p.exists():shutil.copyfile(p,runtime/p.name);entries.append(dict(path='runtime/'+p.name,sha256=sha(p)))
 p=BASE/'work/rabbit-reorder-linux-aarch64'
 if p.exists():shutil.copyfile(p,runtime/p.name);entries.append(dict(path='runtime/'+p.name,sha256=sha(p)))
 return entries
def copy_file(src,dest):
 src=Path(src);dest=Path(dest)
 if src.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
def environment():
 return dict(platform=platform.platform(),machine=platform.machine(),python=platform.python_version(),host_resources=(BASE/'logs/host-resource.txt').read_text(),CPU_only=True,no_NPU=True,dependencies='isolated deps/python and KaHyPar1.3.7; package versions and exact build options in logs; genuine Rabbit in local Alpine ARM VM',time_definition='per-job wall times; queue waits recorded separately after global queue activation; historical T21 costs retain original provenance; new order timers include cached CSR mmap-object setup',current_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
