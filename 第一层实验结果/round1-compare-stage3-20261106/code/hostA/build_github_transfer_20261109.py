import ast,csv,datetime,hashlib,io,json,pathlib,shutil,tarfile
import numpy as np
B=pathlib.Path(__file__).resolve().parents[1];P=B/'transfer-preparation-20261109';OUT=P/'packages';OUT.mkdir(exist_ok=True)
def sha(p):
 with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvwrite(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True);fields=list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def binary(p):
 if any(x in ['deps','build','__pycache__','node_modules','.git'] for x in p.parts):return 'third-party/build/cache directory'
 if p.suffix in ['.dylib','.so','.o','.a','.exe','.dll','.pyc']:return 'compiled binary/library'
 with p.open('rb') as f:magic=f.read(4)
 if magic in [b'\x7fELF',b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xfe\xed\xfa\xcf'] or magic[:2]==b'MZ':return 'executable binary magic'
 return None
exclusions=[];packages=[];changes=[]
def copytree(src,dst,label):
 fs=[p for p in src.rglob('*') if p.is_file()];original=[]
 for p in fs:
  rel=p.relative_to(src);why=binary(p)
  if why:exclusions.append(dict(package=label,path=rel.as_posix(),bytes=p.stat().st_size,sha256=sha(p),reason=why));continue
  q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);data=p.read_bytes();q.write_bytes(data);h=hashlib.sha256(data).hexdigest();original.append(dict(path=rel.as_posix(),sha256=h,bytes=len(data)))
  if sha(p)!=h:changes.append(dict(package=label,path=rel.as_posix(),note='source changed while copying live snapshot; archived bytes have their own hash'))
 return dict(original_files=len(fs),original_bytes=sum(p.stat().st_size for p in fs),included_files=len(original),included_bytes=sum(x['bytes'] for x in original)),original
def pack(src,name,stats):
 archive=OUT/(name+'.tar.gz');assert not archive.exists()
 files={p.relative_to(src).as_posix():sha(p) for p in src.rglob('*') if p.is_file()}
 with tarfile.open(archive,'w:gz',compresslevel=6) as t:
  for rel in sorted(files):t.add(src/rel,arcname=name+'/'+rel,recursive=False)
 with tarfile.open(archive) as t:
  members=t.getmembers();assert len(members)==len(files)
  for m in members:
   assert m.isfile() and not m.name.startswith('/') and '..' not in pathlib.PurePosixPath(m.name).parts
   rel=m.name[len(name)+1:]
   with t.extractfile(m) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==files[rel]
 packages.append(dict(name=name,archive=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),**stats))

for name in ['rq3-validate-20261106','round1-compare-20261106']:
 src=B/'delivery/第一层实验结果'/name;dst=P/'staging'/name;assert not dst.exists();dst.mkdir(parents=True)
 stats,inventory=copytree(src,dst,name);dump(P/(name+'-included-inventory.json'),inventory)
 # Check the immutable source directory against the original sealed checksum list.
 for line in (src/'SHA256SUMS').read_text().splitlines():
  h,rel=line.split('  ',1);assert sha(src/rel)==h,(name,rel)
 pack(dst,name,dict(source_directory=str(src),snapshot=False,**stats))

name='round1-compare-stage3-inprogress-20261109';dst=P/'staging'/name;assert not dst.exists();dst.mkdir(parents=True)
col=P/'view/work/stage3-collected';copytree(col,dst,name)
for folder in ['stage3-cases','stage3-evaluations','stage3-diagnostics','stage3-eval-catalog','stage3-post-catalog','stage3-partial-post','stage3-independent']:
 src=B/'work'/folder
 if src.exists():copytree(src,dst/'raw'/folder,name)
for p in (B/'work/post-e').glob('stage3-*'):
 if p.is_dir():copytree(p,dst/'raw/post-e'/p.name,name)
for p in (B/'logs').glob('stage3-*'):
 if p.is_file() and not binary(p):q=dst/'logs'/p.name;q.parent.mkdir(exist_ok=True);q.write_bytes(p.read_bytes())
for folder in ['cpu-slot-starts','memory-guards','layout-context-backends']:
 if (B/'logs'/folder).exists():copytree(B/'logs'/folder,dst/'logs'/folder,name)
for fn in ['post_e_job.py','ls_runtime.py','native.py','layouts_flatco.cpp','layouts_cached.cpp','collect_stage3.py']:
 q=dst/'code'/fn;q.parent.mkdir(exist_ok=True);q.write_bytes((B/'scripts'/fn).read_bytes())
dump(dst/'SNAPSHOT.json',dict(state='INPROGRESS',created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),coverage=json.loads((col/'coverage.json').read_text()),not_a_final_seal=True,notes='Original completed directories unchanged. Snapshot copied while local stage3 jobs continue; remote 20 cases not recovered. INCOMPLETE can mean pending, interrupted, timed out, or guard-rejected; consult reasons and raw records.'))
fs=[p for p in dst.rglob('*') if p.is_file()];pack(dst,name,dict(source_directory='isolated read-only collection from work/ + raw stage3 evidence',snapshot=True,original_files=len(fs),original_bytes=sum(p.stat().st_size for p in fs),included_files=len(fs),included_bytes=sum(p.stat().st_size for p in fs)))

supp=P/'supplements';supp.mkdir(exist_ok=True);rounds=[];layouts=[];summary=[]
for folder in sorted((B/'work/post-e').iterdir()):
 if not folder.is_dir():continue
 rec=folder/'record.json';cp=folder/'last-completed-sweep.checkpoint.json';catalog=(B/'work/stage3-post-catalog' if folder.name.startswith('stage3-') else B/'work/post-catalog')/(folder.name+'.json')
 r=json.loads(rec.read_text()) if rec.exists() else json.loads(catalog.read_text()) if catalog.exists() else {}
 if not r:continue
 h=r.get('diagnostics',{}).get('history') or [];source=rec
 if not h and cp.exists():h=json.loads(cp.read_text()).get('history',[]);source=cp
 if not h:
  lp=B/'logs'/('stage3-post-'+folder.name+'.stdout' if folder.name.startswith('stage3-') else 'post-e-'+folder.name+'.stdout')
  if lp.exists():
   for line in lp.read_text(errors='replace').splitlines():
    if line.startswith('LS '):
     try:h.append(ast.literal_eval(line[3:]))
     except (ValueError,SyntaxError):pass
   if h:source=lp
 base=dict(matrix=r.get('matrix',''),candidate=r.get('member',r.get('method','')),tau=r.get('tau',''),scope='stage3-inprogress' if folder.name.startswith('stage3-') else 'T23-stages1-2',pipeline_status=r.get('status','NO_FINAL_RECORD') if rec.exists() else 'NO_FINAL_RECORD',completed_logged_rounds=len(h),max_rounds=10,reused=bool(r.get('reuse')),source_path=str(source.relative_to(B)) if source.exists() else '',source_sha256=sha(source) if source.exists() else '')
 prev=0.
 for x in h:
  elapsed=float(x['elapsed']);rounds.append(dict(base,sweep=x['sweep'],accepted=x['accepted'],logged_cumulative_seconds=elapsed,round_wall_delta_seconds=elapsed-prev,seconds_scope='difference of successive elapsed log markers; includes between-marker overhead, not isolated native kernel time'));prev=elapsed
 summary.append(dict(base,logged_round_total_seconds=prev if h else '',original_post_pipeline_seconds=r.get('seconds','') if rec.exists() else '',post_lS_seconds_separately_logged='NO' if not h else 'elapsed markers only',missing_history_reason='' if h else 'not logged here / frozen T21 reuse / no completed round; not rerun'))
 rp=folder/'rows.json'
 if rp.exists():
  for row in json.loads(rp.read_text()):layouts.append(dict(base,diag=row['diag'],d_rule=row['d_rule'],condition_status=row['status'],layout_request_seconds=row.get('d_sec',''),D_greedy_isolated_seconds='',tail_co_isolated_seconds='',reason='d_sec covers lc.layout including D-greedy when enabled and tail-co, plus lc.metrics; components not separately timed',post_sec=row.get('post_sec',''),rows_source=str(rp.relative_to(B)),rows_sha256=sha(rp)))
csvwrite(supp/'post-E-round-times.csv',rounds);csvwrite(supp/'post-E-timing-summary.csv',summary);csvwrite(supp/'post-E-layout-times.csv',layouts)
deg=np.load(B/'work/matrices/reddit/degrees.npy',mmap_mode='r');res=[];n=len(deg);nnz=int(np.sum(deg,dtype=np.int64));NB=(n+15)//16;CWords=(n+63)//64
for tau in [53,153]:
 mask=deg<=tau;D=int(np.count_nonzero(mask));K=(n-D+15)//16;words=(K+63)//64;estimate=n*words*8+K*NB*2+K*CWords*16+NB*words*16+nnz*48+K*1024
 res.append(dict(matrix='reddit',tau=tau,n=n,residual_rows_A0_degree_rule=D,residual_nnz_A0=int(np.sum(deg[mask],dtype=np.int64)),residual_nnz_A1=int(np.sum(deg[mask],dtype=np.int64))+D,kept_rows=n-D,W=16,K_windows=K,NB_all_row_blocks=NB,words=words,CWords=CWords,LS_preflight_estimate_bytes=estimate,budget_bytes=8*2**30,degree_sha256=sha(B/'work/matrices/reddit/degrees.npy')))
csvwrite(supp/'reddit-residual-and-workspace.csv',res)
planned=json.loads((B/'logs/stage3-planned-cases.json').read_text());index={(r['matrix'],r['method'],str(r['W']),str(r['seed'])):r['case_id'] for r in planned};assignment=json.loads((B/'handoff/T23-split-20261109/assignment.json').read_text());remote={r['case_id'] for r in assignment['remote_cases']};states=[]
for r in csv.DictReader((col/'results.csv').open()):
 if r['matrix'] not in ['ogbn-products','mycielskian15']:continue
 key=index[(r['matrix'],r['member'],r['W'],r['seed'])];record=B/'work/stage3-cases'/key/'record.json';commands=list((B/'logs').glob('stage3-*'+key+'*.command.json'));running=any(json.loads(p.read_text()).get('status')=='RUNNING' for p in commands)
 reason=r.get('note','')
 if not record.exists():reason+='; remote-owned, not received' if key in remote else '; local phase active/queued; case not final' if running else '; local case not yet dispatched/completed'
 states.append({**{k:r.get(k,'') for k in ['matrix','member','W','seed','diag','tau','placement','d_rule','source','status']},'case_id':key,'owner':'other computer' if key in remote else 'local','case_final_record_present':record.exists(),'reason':reason,'snapshot_not_final':True})
csvwrite(supp/'products-mycielskian-condition-status.csv',states)
formula='''LS preflight (bytes), scripts/ls_runtime.py: n*ceil(K/64)*8 + K*NB*2 + K*ceil(n/64)*16 + NB*ceil(K/64)*16 + nnz(A0)*48 + K*1024; K=ceil(kept_rows/W), NB=ceil(n/W). Limit=8589934592 bytes.\nco-pair fallback layouts_flatco.cpp: skip windows with >400 residual vertices; count exact distinct co-occurring pairs; reject once pairs.size()>100000000. The error text mentions an 8GiB workspace estimate; this is NOT a measured peak RSS and not a logged exact byte value.\nv7 flat-table preflight: bound=min(enumerated_pairs, choose(residual_points,2),100000001); estimated bytes=context capacities + per-window/point capacities + capacity_for(bound)*(sizeof(uint64_t)+sizeof(uint32_t)) + bound*sizeof(tuple<int,int,int>) + 1GiB. If >8GiB, fallback to original map; no truncation. Actual per-condition vector capacities were not logged, so do not invent a numeric byte estimate.\nD/tail-co timings: original d_sec includes lc.layout + lc.metrics; a D-greedy row also includes K ordering inside layout. Separate D-greedy/tail-co seconds are unavailable from existing logs. No rerun or inferred subtraction is used.\nA1 residual nnz adds one diagonal per residual row; membership D uses fixed A0 degree.\n'''
(supp/'workspace-and-timing-definitions.txt').write_text(formula)
for f in ['ls_runtime.py','post_e_job.py','layouts_flatco.cpp','layouts_cached.cpp','native.py']:
 q=supp/'source'/f;q.parent.mkdir(exist_ok=True);q.write_bytes((B/'scripts'/f).read_bytes())
text='三项补充材料；只从已有记录摘取，未重跑实验。阶段3为运行中快照。\n\n'+formula
for p in sorted(supp.glob('*.csv')):text+='\n\n=== '+p.name+' ===\n'+p.read_text()
(P/'SUPPLEMENTS.txt').write_text(text)
csvwrite(P/'excluded-files.csv',exclusions);dump(P/'transfer-build.json',dict(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),packages=packages,exclusions=exclusions,live_copy_changes=changes,total_archive_bytes=sum(p['archive_bytes'] for p in packages),limit_bytes=int(1.5*2**30),over_limit=sum(p['archive_bytes'] for p in packages)>1.5*2**30))
assert sum(p['archive_bytes'] for p in packages)<=1.5*2**30, 'STOP: archive total exceeds1.5GiB'
print(json.dumps({'packages':packages,'total_archive_bytes':sum(p['archive_bytes'] for p in packages),'exclusions':len(exclusions),'timing_round_rows':len(rounds),'layout_rows':len(layouts),'status_rows':len(states),'live_copy_changes':len(changes)},ensure_ascii=False),flush=True)
