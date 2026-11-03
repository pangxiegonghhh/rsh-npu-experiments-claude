"""E2 shared-L1 handoff fixtures, state model, strict validation and archival."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os
from pathlib import Path
import random, shutil, struct, subprocess, tarfile, time
import numpy as np
from e1_experiment import codec, cpu_decode, oracle, sha, write, unwrap

US=(0,1,15,16,17,31,32,37,63,64,65,127,128,129,255,256,257)

def model(tiles:int,q:int,depth:int,seed:int,omit_idle:bool=False,early_release:bool=False)->dict:
    """Three independently scheduled actors; abort on deadlock or overwrite."""
    packs=(tiles+q-1)//q; rng=random.Random(seed); ptr=[0,0,0]
    aic_ready=[0]*depth;partial=[[0,0] for _ in range(depth)];free=[[0]*depth for _ in range(2)]
    contents=[{} for _ in range(depth)];released=[True]*depth;maxcount=0
    # Producer actions: wait -> write -> ready; trailing drains. Consumer wait -> consume -> free.
    streams=[]
    for sub in range(2):
        s=[]
        for p in range(packs):
            slot=p%depth
            if p>=depth:s.append(('wait',slot,p))
            for i in range(sub,min(q,tiles-p*q),2):s.append(('write',slot,p,i))
            if not(omit_idle and min(q,tiles-p*q)<=sub):s.append(('ready',slot,p))
        for slot in range(min(depth,packs)):s.append(('wait',slot,packs))
        streams.append(s)
    consumer=[]
    for p in range(packs):
        order=('take','free','consume') if early_release else ('take','consume','free')
        consumer += [(op,p%depth,p) for op in order]
    streams.append(consumer)
    limit=sum(map(len,streams))+5
    for _ in range(limit):
        choices=[]
        for a,s in enumerate(streams):
            if ptr[a]>=len(s):continue
            e=s[ptr[a]];slot=e[1]
            if e[0]=='wait' and free[a][slot]==0:continue
            if e[0]=='take' and aic_ready[slot]==0:continue
            choices.append(a)
        if not choices:
            assert all(ptr[a]==len(s) for a,s in enumerate(streams)),"DEADLOCK"
            break
        a=rng.choice(choices);e=streams[a][ptr[a]];kind,slot,p=e[:3]
        if kind=='wait':free[a][slot]-=1
        elif kind=='write':
            # A slot is considered owned until consumer returns it.
            old=contents[slot].get(e[3]);assert old is None or old[0]<p and released[slot],"OVERWRITE"
            contents[slot][e[3]]=(p,e[3])
        elif kind=='ready':
            partial[slot][a]+=1
            if min(partial[slot]):
                partial[slot][0]-=1;partial[slot][1]-=1;aic_ready[slot]+=1;released[slot]=False
        elif kind=='take':aic_ready[slot]-=1
        elif kind=='consume':
            assert all(contents[slot].get(i)==(p,i) for i in range(min(q,tiles-p*q))),"WRONG_GENERATION"
        else:
            released[slot]=True
            for x in range(2):free[x][slot]+=1
        maxcount=max(maxcount,*aic_ready,*free[0],*free[1]);assert maxcount<=2
        ptr[a]+=1
    assert not any(aic_ready) and not any(free[0]) and not any(free[1])
    return {'status':'PASS','max_pending_per_flag':maxcount}

def prepare(root:Path)->None:
    assert not (root/'inputs').exists()
    (root/'inputs').mkdir(parents=True);enc=codec();rng=np.random.default_rng(2026102202);infos=[]
    def save(base:str,u:int,n:int,a:np.ndarray,cols:np.ndarray,group:str,rounds:int=1,cap:int=1,select:int|None=None):
        t=(u+15)//16;kp=max(16,t*16);npad=(n+15)//16*16;orig=521
        padded=np.zeros((16,kp),'<f2');padded[:,:u]=a
        tiles=padded[:,:t*16].reshape(16,t,16).transpose(1,0,2).copy()
        b=np.zeros((orig+1,npad),'<f2')
        for row in range(orig):
            for f in range(n):b[row,f]=((row*7+f*3)%31-15)/8
        if select is not None:
            b[:]=0
            for k,col in enumerate(cols):
                if k//16==select:b[int(col),k%16]=1
        for kind,name in ((1,'bitmap'),(2,'local_index')):
            desc,payload=enc.encode(tiles,name,[min(16,u-i*16) for i in range(t)])
            for q in (1,2,4,8):
                for depth in (1,2):
                    case=root/'inputs'/f'{base}_k{kind}_q{q}_d{depth}_r{rounds}_c{cap}';case.mkdir()
                    (case/'desc.bin').write_bytes(desc);(case/'payload.bin').write_bytes(payload)
                    cols.astype('<u4').tofile(case/'cols.bin');a.astype('<f2').tofile(case/'original-a.bin');b.tofile(case/'b.bin')
                    np.array([u,kp,n,npad,orig,t,len(desc),len(payload)],'<u4').tofile(case/'config.bin')
                    np.array([q,depth,rounds,cap,11],'<u4').tofile(case/'run.bin')
                    expected,refs,gold=oracle(case);assert np.array_equal(cpu_decode(case),expected)
                    info={'id':case.name,'U':u,'N':n,'Kp':kp,'Np':npad,'tiles':t,'q':q,'depth':depth,
                          'rounds':rounds,'capture':cap,'kind':kind,'group':group,'selector_tile':select,
                          'sha256':{p.name:sha(p) for p in case.glob('*.bin')}}
                    write(case/'case.json',info);infos.append(info)
    def logical(u:int,pat:int):
        cols=np.sort(rng.choice(521,u,replace=False)).astype('<u4')
        a=rng.choice(np.array([-2,-1,-.5,.25,.5,1,2],np.float16),(16,u))
        a[rng.random((16,u))>(.125 if pat==0 else .875)]=0
        for k in range(u):a[k%16,k]=(k%7+1)/8
        return a,cols
    for u in US:
        for n in (17,64):
            for p in (0,1):
                a,cols=logical(u,p);save(f'main_u{u}_n{n}_p{p}',u,n,a,cols,'main')
    for t in (1,3,9):
        u=(t-1)*16+1 if t>1 else 16;a,cols=logical(u,1)
        for selected in range(t):save(f'select_t{t}_s{selected}',u,16,a,cols,'selector',select=selected)
    a,cols=logical(257,0)
    for cap in (0,1):save(f'long_c{cap}',257,64,a,cols,'long',257,cap)
    save('repeat_core',257,64,a,cols,'repeat_core',17,1)
    assert len(infos)==1344,len(infos)
    write(root/'manifest.json',infos)
    models=[]
    for tiles in range(18):
        for q in (1,2,4,8):
            for depth in (1,2):
                for seed in range(16):models.append(model(tiles,q,depth,seed))
    for label,kwargs in [('missing_idle',{'omit_idle':True}),('early_release',{'early_release':True})]:
        try:model(17,1,2,0,**kwargs)
        except AssertionError:pass
        else:raise AssertionError(label+' accepted')
    write(root/'state-model.json',{'status':'PASS','schedules':len(models),'negative_protocols_rejected':2,'max_pending':2})
    # Address contract is shared rather than independently allocated.
    budgets=[]
    for q in (1,2,4,8):
        for depth in (1,2):
            for npad in (16,32,64):
                base=depth*q*512
                assert base%512==0 and base+32*npad<=524032
                budgets.append({'q':q,'depth':depth,'Np':npad,'A_L1':[0,base],
                                'B_L1':[base,base+32*npad],'L0A':512,'L0B':32*npad,'L0C':64*npad,'AIV_UB':512})
    write(root/'address-budgets.json',budgets)
    invalid=root/'invalid';invalid.mkdir();bad=[]
    base=next(x for x in infos if x['U']==37 and x['q']==1 and x['depth']==1)
    for label,at,value in [('q0',0,0),('q3',0,3),('depth0',4,0),('depth3',4,3),('round0',8,0),('round258',8,258),('capture2',12,2),('stall65',16,65)]:
        dst=invalid/label;shutil.copytree(root/'inputs'/base['id'],dst)
        data=bytearray((dst/'run.bin').read_bytes());struct.pack_into('<I',data,at,value);(dst/'run.bin').write_bytes(data);bad.append(label)
    write(root/'invalid-manifest.json',bad)
    write(root/'preflight.json',{'status':'PASS','cases':len(infos),'main':1088,'selectors':208,'long':32,'repeat_core':16,'state_schedules':len(models)})
    print('E2_LOCAL_PREFLIGHT_PASS',len(infos),flush=True)

def validate(case:Path,dest:Path,count:int)->dict:
    x=json.loads((case/'case.json').read_text())
    for f,want in x['sha256'].items():assert sha(case/f)==want,f
    a,refs,c=oracle(case);tiles=x['tiles'];q=x['q'];depth=x['depth'];rounds=x['rounds'];packs=(tiles+q-1)//q
    host=json.loads((dest/'host.json').read_text());g=host['guard_byte']
    assert host['status']=='SYNC_OK' and host['iterations']==count and host['input_checked_each_call']
    for prefix in ('output','snapshot','trace','done'):
        assert sorted(int(p.stem[len(prefix)+1:]) for p in dest.glob(prefix+'-*.bin'))==list(range(count)),(dest,prefix)
    tile_a=a[:,:tiles*16].reshape(16,tiles,16).transpose(1,0,2).copy()
    for it in range(count):
        ab=((it//2)%2);both=(it%2+ab)%2
        out=np.frombuffer(unwrap(dest/f'output-{it}.bin',rounds*c.nbytes,g),'<f4').reshape(rounds,16,x['Np'])
        assert np.isfinite(out).all()
        for e in range(rounds):assert np.array_equal(out[e],-c if (e%2+both)%2 else c),(case.name,it,e,'C')
        snap=unwrap(dest/f'snapshot-{it}.bin',rounds*max(1,tiles)*512,g)
        if x['capture'] and tiles:
            actual=np.frombuffer(snap,'<f2').reshape(rounds,tiles,16,16)
            for e in range(rounds):assert np.array_equal(actual[e],-tile_a if (e%2+ab)%2 else tile_a),(case.name,it,e,'A')
        else:assert snap==bytes([0xab])*len(snap)
        tr=np.frombuffer(unwrap(dest/f'trace-{it}.bin',rounds*max(1,packs)*3*128,g),'<u4').reshape(rounds,max(1,packs),3,32)
        assert np.all(tr[...,8:]==0xcdcdcdcd)
        if not packs:assert np.all(tr==0xcdcdcdcd)
        for e in range(rounds):
            for p in range(packs):
                active=min(q,tiles-p*q);seq=e*packs+p+1
                for role in range(3):
                    owned=active if role==0 else len(range(role-1,active,2))
                    free=seq if role==0 else e*packs+max(0,p-depth+1)
                    want=[e,p,p%depth,active,owned,seq,free,0xe200+role]
                    assert tr[e,p,role,:8].tolist()==want,(case.name,e,p,role,tr[e,p,role,:8].tolist(),want)
        done=np.frombuffer(unwrap(dest/f'done-{it}.bin',3*128,g),'<u4').reshape(3,32)
        assert np.all(done[:,8:]==0xcdcdcdcd)
        for role in range(3):
            owned=tiles if role==0 else sum(len(range(role-1,min(q,tiles-p*q),2)) for p in range(packs))
            want=[rounds,packs,rounds*packs,rounds*packs,rounds*owned,role,q,depth]
            assert done[role,:8].tolist()==want,(case.name,role,'done')
    payload=bytearray((case/'payload.bin').read_bytes());bb=bytearray((case/'b.bin').read_bytes())
    if ((count-1)//2)%2:
        for off,z,kind,vk,size in struct.iter_unpack('<QHBBI',(case/'desc.bin').read_bytes()):
            for p in range(off+(32 if kind==1 else z+z%2),off+size,2):payload[p+1]^=0x80
    if (count-1)%2:
        for p in range(1,len(bb),2):bb[p]^=0x80
    for name,want in [('payload',payload),('b',bb),*[(name,(case/(name+'.bin')).read_bytes()) for name in ('desc','cols','config','run')]]:
        assert unwrap(dest/(name+'-after.bin'),len(want),g)==want,(case.name,name)
    return {'case_id':case.name,'status':'PASS','iterations':count,'rounds':rounds,'packages_per_round':packs,
            'max_abs_error':0,'depth':depth,'q':q,'sequence_complete':True}

def run(root:Path)->None:
    infos=json.loads((root/'manifest.json').read_text());commands=[];checks=[]
    def invoke(argv:list[str],label:str,timeout:int=180,env:dict|None=None):
        p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
        rec={'argv':argv,'label':label,'pid':p.pid,'start_unix':time.time()};commands.append(rec);write(root/'commands.json',commands)
        try:out,_=p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill();out,_=p.communicate();(root/'logs'/f'{label}.log').write_bytes(out);rec.update(returncode=p.returncode,end_unix=time.time(),timeout=True);write(root/'commands.json',commands);raise
        (root/'logs'/f'{label}.log').write_bytes(out);rec.update(returncode=p.returncode,end_unix=time.time());write(root/'commands.json',commands)
        return p.returncode,out
    (root/'logs').mkdir(exist_ok=True);negative=[]
    for name in json.loads((root/'invalid-manifest.json').read_text()):
        rc,out=invoke([str(root/'build/e2_runner'),'--validate',str(root/'invalid'/name)],'reject-'+name)
        assert rc==1 and b'CALL_OK' not in out;negative.append({'id':name,'status':'REJECTED_BEFORE_ACL'})
    write(root/'negative-checks.json',negative)
    for depth in (1,2):
        subset=[x for x in infos if x['depth']==depth]
        for batch,start in enumerate(range(0,len(subset),32)):
            chunk=subset[start:start+32];lst=root/f'd{depth}-b{batch}.txt';lst.write_text(''.join(str(root/'inputs'/x['id'])+'\n' for x in chunk))
            rc,out=invoke([str(root/'build/e2_runner'),str(lst),str(root/f'results/depth-{depth}'),'1'],f'd{depth}-b{batch}',300)
            assert rc==0,(depth,batch)
            for x in chunk:checks.append(validate(root/'inputs'/x['id'],root/f'results/depth-{depth}'/x['id'],1))
            write(root/'checks.json',checks);write(root/'progress.json',{'depth':depth,'validated':len(checks),'total':len(infos),'at':time.time()})
            print('E2_PROGRESS',depth,len(checks),len(infos),flush=True)
    repeated=[x for x in infos if x['group']=='repeat_core'];assert len(repeated)==16
    repeat=[]
    for process in range(3):
        lst=root/f'repeat-{process}.txt';lst.write_text(''.join(str(root/'inputs'/x['id'])+'\n' for x in repeated))
        env=dict(os.environ);env['E2_GUARD_BYTE']=str(0x36 if process%2 else 0x5a)
        rc,out=invoke([str(root/'build/e2_runner'),str(lst),str(root/f'results/repeat-{process}'),'10'],f'repeat-{process}',300,env)
        assert rc==0
        for x in repeated:
            c=validate(root/'inputs'/x['id'],root/f'results/repeat-{process}'/x['id'],10);c['process']=process;repeat.append(c)
        write(root/'repeat-checks.json',repeat)
    rounds=sum(x['rounds'] for x in checks)+sum(x['rounds']*x['iterations'] for x in repeat)
    write(root/'summary.json',{'status':'PASS','main_cases':len(checks),'repeat_calls':480,'kernel_calls':len(checks)+480,
          'output_rounds':rounds,'max_abs_error':0,'depths':[1,2],'q':[1,2,4,8],'Residual':False,'GM_A_feed':False,'E3_started':False,'end_unix':time.time()})
    print('E2_ALL_PASS',rounds,flush=True)

def close(root:Path)->None:
    assert (root/'driver.rc').read_text().strip()=='E2_RC=0'
    assert json.loads((root/'summary.json').read_text())['status']=='PASS'
    for listname in ('expected-source-sha256.json','binary-sha256.json'):
        for name,want in json.loads((root/listname).read_text()).items():assert sha(root/name)==want,name
    write(root/'closed.json',{'status':'PASS','at':time.time(),'sources_binaries_unchanged':True})
    files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='file-hashes.json' and '__pycache__' not in str(p))
    write(root/'file-hashes.json',{str(p.relative_to(root)):sha(p) for p in files})
    archive=root.parent/(root.name+'-closed.tar.gz')
    with tarfile.open(archive,'w:gz') as tf:
        for p in files+[root/'file-hashes.json']:tf.add(p,arcname=str(p.relative_to(root)),recursive=False)
    info={'archive':archive.name,'sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files)+1,'status':'PASS'}
    write(root.parent/(root.name+'-closed-transfer.json'),info);print(json.dumps(info),flush=True)

def replay(root:Path)->dict:
    main=json.loads((root/'checks.json').read_text());repeat=json.loads((root/'repeat-checks.json').read_text())
    for x in main:validate(root/'inputs'/x['case_id'],root/f"results/depth-{x['depth']}"/x['case_id'],1)
    for x in repeat:validate(root/'inputs'/x['case_id'],root/f"results/repeat-{x['process']}"/x['case_id'],10)
    if (root/'smoke-checks.json').exists():
        for x in json.loads((root/'smoke-checks.json').read_text()):validate(root/'inputs'/x['case_id'],root/'results/smoke'/x['case_id'],1)
    hashes=json.loads((root/'file-hashes.json').read_text())
    for name,want in hashes.items():assert sha(root/name)==want,name
    return {'status':'PASS','main_cases':len(main),'repeat_calls':sum(x['iterations'] for x in repeat),'hashes_verified':len(hashes),'max_abs_error':0,'raw_evidence_modified':False}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','run','close','replay']);ap.add_argument('root',type=Path);a=ap.parse_args()
    result=globals()[a.mode](a.root)
    if result is not None:print(json.dumps(result,indent=2))
