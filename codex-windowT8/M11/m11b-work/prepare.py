"""M11b input registration; CPU only, no access to original mutable outputs."""
from pathlib import Path
import csv, json, random, struct, hashlib, importlib.util, shutil
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'m11-work'
spec=importlib.util.spec_from_file_location('old_prep',ROOT/'original_prepare.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

def put(path, values):path.write_bytes(struct.pack('<'+'I'*len(values),*values))
def csvout(path, rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    out=ROOT/'inputs';out.mkdir(exist_ok=True);cases=[];audit=[];structures=[]
    base=ROOT/'prep/cora-B1-windows.csv'
    gaps=[int(g) for r in csv.DictReader(base.open()) for g in r['seg_gaps'].split(';') if g]
    assert gaps and min(gaps)>=1
    (ROOT/'prep/cora-gap-distribution.json').write_text(json.dumps(dict(gaps=gaps,source='Cora A0 W16 B1 windows.csv seg_gaps',sampling='empirical marginal with replacement, joint lengths/gaps not preserved'),indent=2))
    geom={}
    for u,r in [(36,18),(56,50),(64,32)]:
        for layout in ['random-gap','cora-like']:
            seed=20261115+u*100+r+(10000 if layout=='cora-like' else 0)
            rng=random.Random(seed);lens=[u//r+(i<u%r) for i in range(r)];rng.shuffle(lens)
            gg=[rng.choice(gaps) if layout=='cora-like' else rng.randint(1,2) for _ in range(r-1)]
            rows=[];pos=0
            for i,h in enumerate(lens):
                rows.extend(range(pos,pos+h));pos+=h+(gg[i] if i<r-1 else 0)
            name=f'M11b-B2-u{u}-r{r}-{layout}';geom[name]=[rows]
            structures.append(dict(geometry=name,U=u,R=r,layout=layout,seed=seed,segment_lengths=lens,gaps=gg,source_rows=rows))
    # New-batch control only: 12 B1 high-N/hot points; not a rerun of the full M11.
    cora=json.loads((ROOT/'prep/Cora-B1-rows.json').read_text())
    geom['M11b-B2-cora-B1-control']=cora
    stage=[];gate=[];strong=[]
    for name,windows in geom.items():
        refs=[];meta=[];maxrow=max(max(w) for w in windows)+1
        for wi,rows in enumerate(windows):
            for ti in range((len(rows)+15)//16):
                chunk=rows[ti*16:ti*16+16];refs+=chunk+[0xffffffff-i for i in range(16-len(chunk))];meta.extend([wi,ti,int((ti+1)*16>=len(rows))])
        for dtype,es in [('FP16',2),('FP32',4)]:
            for n in [128,256]:
                physical=[r if r<0xffffff00 else maxrow+16+0xffffffff-r for r in refs];cmd=[];off=[0];calls=[0,0,0]
                for ti in range(len(meta)//3):
                    rr=physical[ti*16:ti*16+16];cc=old.commands(rr,n,maxrow);cmd+=cc;off.append(len(cmd));a=old.cpu_layout(rr,n,es)
                    calls[0]+=len(cc);calls[1]+=a['ordinary_row_calls'];calls[2]+=a['ordinary_stripe_calls']
                for path in range(3):
                    title=f'{name}-{dtype}-n{n}-hot-p{path}';g=(524032//(2*16*n*es))//2*2
                    cfg=[int(es==4),n,len(meta)//3,g,0,0,24,1,path,len(windows),maxrow,0,maxrow,0,0,0,0,calls[path],0,0,0,0,0,0]+meta+physical
                    for suffix,vals in [('config',cfg),('commands',[v for c in cmd for v in c]),('offsets',off),('rows',refs),('lengths',list(map(len,windows)))]:put(out/(title+'.'+suffix+'.bin'),vals)
                    selected=len(set(r for r in refs if r<0xffffff00));reps=min((32*1024**2+selected*n*es-1)//(selected*n*es),(2*1024**3//(n*es)-16)//maxrow)
                    audit.append(dict(case_id=title,status='PASS',tiles=cfg[2],calls=calls[path],span=maxrow,selected_rows=selected,hot_unique_bytes=reps*selected*n*es))
                    cases.append(dict(item='M11b-2',case_id=title,kernel='K-H' if dtype=='FP16' else 'K-D',kernel_variant=['nd2nz','copy-row','copy-colstrip'][path],layout='cora-replay-control' if 'control' in name else name.split(f'-r{len(old.pieces(windows[0]))}-')[-1],dtype=dtype,N=n,U=sum(map(len,windows)),R=sum(len(old.pieces(w)) for w in windows),cache='hot',g=g,control='control' in name,expected_calls_per_replay=calls[path]))
                    stage.append(title);gate.append(title)
                    scfg=cfg.copy();scfg[9]=cfg[2]
                    for ti in range(cfg[2]):scfg[24+ti*3:24+ti*3+3]=[ti,0,1]
                    slens=[sum(r<0xffffff00 for r in refs[ti*16:ti*16+16]) for ti in range(cfg[2])];sn='M11b-strong-'+title
                    for suffix,vals in [('config',scfg),('commands',[v for c in cmd for v in c]),('offsets',off),('rows',refs),('lengths',slens)]:put(out/(sn+'.'+suffix+'.bin'),vals)
                    strong.append(sn)
    # B3 correctness-only: directly consume the load result, no later overwrite.
    b3={5:[],6:[]};b3cases=[]
    for dtype,es in [('FP16',2),('FP32',4)]:
        for n in [16,32,64,128,256]:
            for h in [1,2,4,8,16]:
                rr=list(range(h))+list(range(h+16,h+16+16-h));refs=list(range(h))+[0xffffffff-i for i in range(16-h)];cmd=old.commands(rr,n,h)
                for mode,label in [(5,'plain-only'),(6,'transpose')]:
                    title=f'M11b-B3-{label}-{dtype}-n{n}-h{h}';cfg=[int(es==4),n,1,2,1,1,1,1,0,1,h,0,h+16,0,mode,1,0,0,0,0,h,0,0,0]+[0,0,1]+rr
                    for suffix,vals in [('config',cfg),('commands',[v for c in cmd for v in c]),('offsets',[0,len(cmd)]),('rows',refs),('lengths',[h])]:put(out/(title+'.'+suffix+'.bin'),vals)
                    b3[mode].append(title)
                    b3cases.append(dict(item='M11b-3',case_id=title,variant=label,dtype=dtype,N=n,h=h,logical_bytes=h*n*es,actual_padded_load_bytes=16*n*es,phase='correctness-before-timing',batch=1))
    assert len(stage)==84 and sum(not r['control'] for r in cases)==72
    for name,values in [('stage3',stage),('gate',gate),('strong-gate',strong),('b3-plain',b3[5]),('b3-transpose',b3[6])]: (ROOT/(name+'.list')).write_text('\n'.join(values)+'\n')
    csvout(ROOT/'manifests/cases.csv',cases);csvout(ROOT/'manifests/B3-gate-cases.csv',b3cases)
    (ROOT/'prep/structures.json').write_text(json.dumps(structures,indent=2));(ROOT/'CPU-AUDIT.json').write_text(json.dumps(dict(status='PASS',cases=audit),indent=2))
    (ROOT/'INPUT-SHA256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.bin'))},indent=2))
    print('M11b_CPU_PREP_PASS',len(stage),len(strong),len(b3cases),flush=True)
if __name__=='__main__':main()
