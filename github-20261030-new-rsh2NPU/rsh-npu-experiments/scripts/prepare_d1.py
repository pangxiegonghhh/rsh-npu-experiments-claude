"""D1 exact-layout transforms and host-only event diagnostic build."""
from __future__ import annotations
import hashlib,json,shlex,shutil,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d1'
POINTS=[('FEMLAB_ns3Da',16),('SNAP_email-Enron',64),('SNAP_ca-HepTh',256),('SNAP_web-NotreDame',16),('Schmid_thermal1',64)]
ARGS=['V0','V2','V2-Z/V2','H-V','H-V','G-only/V2','ST-only/V0']
LABELS=['V0','V2','V2-Z','HV-A','HV-B','G-only','ST-only']
KEYS=['ptr','cols','values','cube_ptr','colref','tiles','rowmap','srows','rhs','golden','valid']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def alias(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():assert dst.resolve()==src.resolve()
    else:dst.symlink_to(src.resolve(),target_is_directory=True)
def transform(src,dst,mode):
    cfg=list(map(int,(src/'config.txt').read_text().split()));m,k,n,stride,nnz,ng,nb,ns=cfg
    gp=np.fromfile(src/'cube_ptr.bin',np.int64);rm=np.fromfile(src/'rowmap.bin',np.int32).reshape(ng,16);sr=np.fromfile(src/'srows.bin',np.int32)
    valid=np.zeros(m,np.uint8);kept=np.arange(ng) if mode=='G' else np.flatnonzero(np.diff(gp)>0) if mode=='Z' else np.empty(0,np.int64)
    rows=rm[kept].reshape(-1);present=rows[rows>=0]
    if mode=='Z':valid[:]=1;assert ns==0
    elif mode=='G':valid[present]=1
    else:valid[sr]=1
    newgp=np.r_[0,np.cumsum(np.diff(gp)[kept])].astype(np.int64)
    blockidx=np.concatenate([np.arange(gp[g],gp[g+1]) for g in kept]) if len(kept) else np.empty(0,np.int64)
    changes={'cube_ptr':newgp.tobytes(),'rowmap':rows.astype(np.int32).tobytes(),'srows':(sr if mode=='ST' else np.empty(0,np.int32)).tobytes(),'valid':valid.tobytes()}
    for key,dt,w in [('colref',np.int32,16),('tiles',np.float16,256)]:
        arr=np.fromfile(src/(key+'.bin'),dt).reshape(nb,w);changes[key]=arr[blockidx].tobytes()
    if mode=='Z':
        assert changes['colref']==(src/'colref.bin').read_bytes() and changes['tiles']==(src/'tiles.bin').read_bytes()
        removed=np.setdiff1d(np.arange(ng),kept);ptr=np.fromfile(src/'ptr.bin',np.int32)
        rr=rm[removed].reshape(-1);rr=rr[rr>=0];assert np.all(ptr[rr+1]==ptr[rr])
    cfg[5:]=[len(kept),len(blockidx),len(sr) if mode=='ST' else 0]
    dst.mkdir(parents=True,exist_ok=True)
    for key in KEYS:
        q=dst/(key+'.bin')
        if key in changes:
            if q.exists():assert q.read_bytes()==changes[key],str(q)
            else:q.write_bytes(changes[key])
        else:
            if q.exists():assert sha(q)==sha(src/(key+'.bin'))
            else:q.symlink_to((src/(key+'.bin')).resolve())
    text=' '.join(map(str,cfg))+'\n';p=dst/'config.txt'
    if p.exists():assert p.read_text()==text
    else:p.write_text(text)
    meta={'mode':mode,'source':str(src.relative_to(ROOT)),'source_config':list(map(int,(src/'config.txt').read_text().split())),'config':cfg,'kept_group_indices':kept.tolist(),'removed_groups':ng-len(kept),'unchanged_blocks':mode in ['Z','G'],'full_output':mode=='Z','valid_rows':int(valid.sum()),'empty_valid_scope':not bool(valid.any()),'files_sha256':{key:sha(dst/(key+'.bin')) for key in KEYS},'invariant':'Z deletes whole zero-K groups only; nonempty group members/order/blocks unchanged. G and ST preserve frozen HV ownership; valid mask limits checks.'}
    p=dst/'metadata.json'
    if p.exists():assert read(p)==meta
    else:save(p,meta)
    return meta

def cases():
    facts=[]
    for matrix,n in POINTS:
        src=ROOT/'cases_hv'/matrix/f'N{n}';dst=ROOT/'cases_d1'/matrix/f'N{n}'
        for v in ['V0','V2','H-V']:alias(src/v,dst/v)
        facts.append({'matrix':matrix,'n':n,'root':str(dst.relative_to(ROOT)),'Z':transform(src/'V2',dst/'V2-Z/V2','Z'),'G':transform(src/'H-V',dst/'G-only/V2','G'),'ST':transform(src/'H-V',dst/'ST-only/V0','ST')})
    save(D/'case_transforms.json',{'points':facts})
    return facts

def generate():
    from scripts.prepare_d0 import generate as base
    s=base().read_text();decl=(ROOT/'npu/dispatch.cpp').read_text().split('extern "C" void rsh_launch(void* stream')[0].replace('#include "common.h"\n','')
    s=s.replace('struct Buffer {',decl+'\nstruct Buffer {')
    s=s.replace(' double prepareUs=0,firstUs=0,maxError=0;',' double prepareUs=0,firstUs=0,maxError=0;\n aclrtEvent events[5]{}; std::vector<std::vector<double>> eventSamples;\n ~Case(){for(auto e:events)if(e)aclrtDestroyEvent(e);}')
    s=s.replace('  c.cores=cores;','  c.cores=cores;\n  for(auto& e:events)check(aclrtCreateEventWithFlag(&e,ACL_EVENT_TIME_LINE));')
    a=s.index(' void call(');b=s.index(' void validate(',a)
    s=s[:a]+''' void call(aclrtStream stream,int b){
  check(aclrtRecordEvent(events[0],stream));
  check(aclrtMemsetAsync(out->device,out->size,0,out->size,stream));
  check(aclrtRecordEvent(events[1],stream));
  if(c.groups)check(aclrtMemsetAsync(packed->device,packed->size,0,packed->size,stream));
  check(aclrtRecordEvent(events[2],stream));
  if(kind==0)rsh_launch_vector(stream,c.cores*2,ptr->device,col->device,val->device,gp->device,refs->device,tiles->device,rows->device,rhs[b]->device,packed->device,out->device,config->device);
  else if(kind==1)rsh_launch_cube(stream,c.cores,ptr->device,col->device,val->device,gp->device,refs->device,tiles->device,rows->device,rhs[b]->device,packed->device,out->device,config->device);
  else rsh_launch_mix(stream,c.cores,ptr->device,col->device,val->device,gp->device,refs->device,tiles->device,rows->device,rhs[b]->device,packed->device,out->device,config->device);
  check(aclrtRecordEvent(events[3],stream));
  if(c.groups)rsh_launch_restore(stream,c.cores*2,packed->device,map->device,out->device,config->device);
  check(aclrtRecordEvent(events[4],stream));
  check(aclrtSynchronizeStream(stream));
 }
 void collectEvents(bool retain){
  std::vector<double> v;
  for(int j=0;j<5;++j){float ms=0;check(aclrtEventElapsedTime(&ms,events[j<4?j:0],events[j<4?j+1:4]));v.push_back(ms*1000.0);}
  if(retain)eventSamples.push_back(v);
 }
'''+s[b:]
    s=s.replace('auto e=Clock::now();auto cpuEnd=threadCpuNs();int cpu1=sched_getcpu();','auto e=Clock::now();auto cpuEnd=threadCpuNs();int cpu1=sched_getcpu();\n   cases[j]->collectEvents(!isWarm);')
    needle='  f<<"],\\\"host_trace_schema'
    pos=s.index(needle)
    s=s[:pos]+'''  f<<"],\\\"event_schema\\\":\\\"d1-timeline-v1\\\",\\\"event_fields_us\\\":[\\\"out_clear\\\",\\\"packed_clear\\\",\\\"main_with_B_gather\\\",\\\"restore\\\",\\\"device_span\\\"],\\\"events\\\":[";
  for(size_t i=0;i<cases.size();++i){if(i)f<<',';f<<'[';for(size_t t=0;t<cases[i]->eventSamples.size();++t){if(t)f<<',';f<<'[';for(int j=0;j<5;++j){if(j)f<<',';f<<cases[i]->eventSamples[t][j];}f<<']';}f<<']';}
'''+s[pos:]
    target=ROOT/'diagnostics/d1/profile_runner.cpp';target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_text()==s
    else:target.write_text(s)
    return target

def build():
    src=generate();base=ROOT/'build_v4';dest=ROOT/'build_d1';dest.mkdir(exist_ok=True)
    flags={}
    for line in (base/'CMakeFiles/rsh_runner.dir/flags.make').read_text().splitlines():
        if line.startswith('CXX_') and ' = ' in line:k,v=line.split(' = ',1);flags[k]=shlex.split(v)
    link=shlex.split((base/'CMakeFiles/rsh_runner.dir/link.txt').read_text());objects={str((base/a).relative_to(ROOT)):sha(base/a) for a in link if a.endswith(('.o','.a')) and (base/a).is_file()}
    obj=dest/'profile_runner.cpp.o';exe=dest/'rsh_runner_profile'
    cmd=[link[0],*flags.get('CXX_DEFINES',[]),*flags.get('CXX_INCLUDES',[]),*flags.get('CXX_FLAGS',[]),'-I'+str(ROOT/'npu'),'-c',str(src),'-o',str(obj)]
    index=[i for i,a in enumerate(link) if a.endswith('/runner.cpp.o')];assert len(index)==1
    link[index[0]]=str(obj);link[link.index('-o')+1]=str(exe)
    for label,c in [('compile',cmd),('link',link)]:
        r=subprocess.run(c,cwd=base,capture_output=True,text=True,timeout=180);(D/f'build_{label}.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-3000:]
    for p,h in objects.items():assert sha(ROOT/p)==h
    save(D/'build.json',{'kernel_recompiled':False,'event_source_sha256':sha(src),'event_executable_sha256':sha(exe),'formal_executable_sha256':sha(ROOT/'build_d0/rsh_runner_d0'),'reused_original_objects_sha256':{p:h for p,h in objects.items() if not p.endswith('/runner.cpp.o')},'compile_command':cmd,'link_command':link,'device_api':'aclrtCreateEventWithFlag ACL_EVENT_TIME_LINE; five records, one final stream synchronize; elapsed queries after wall interval','units':'event ms converted to us; wall us','interpretation':'Event intervals include instrumentation and stream gaps. Main includes B gather and all AIC/AIV work; no pure compute claim. Mixed overlap not inferred from isolated branches.'})
    (D/'device_binary').mkdir(exist_ok=True);shutil.copy2(exe,D/'device_binary/rsh_runner_profile');shutil.copy2(ROOT/'build_d0/rsh_runner_d0',D/'device_binary/rsh_runner_formal')
if __name__=='__main__':
    sys.path.insert(0,str(ROOT));D.mkdir(exist_ok=True)
    if '--generate-only' in sys.argv:print(generate())
    elif '--cases-only' in sys.argv:cases()
    else:cases();build()
