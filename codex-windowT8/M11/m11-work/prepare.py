"""Prepare immutable M11 geometry, independent row references, and CPU DMA audit."""
from pathlib import Path
import csv, json, struct, hashlib, random, argparse
ROOT=Path(__file__).resolve().parent
BUNDLE=ROOT/'reference-inputs'

def put(path:Path, values:list[int])->None:
    path.write_bytes(struct.pack('<'+'I'*len(values),*values))

def pieces(rows:list[int])->list[list[int]]:
    out=[]
    for k,row in enumerate(rows):
        if out and row==out[-1][0]+out[-1][1]:out[-1][1]+=1
        else:out.append([row,1,1,0,k,0,0,0])
    return out

def commands(rows:list[int], n:int, zero:int)->list[list[int]]:
    raw=pieces(rows);out=[];i=0
    while i<len(raw):
        p=raw[i].copy();i+=1
        if i<len(raw) and raw[i][1]==p[1] and (raw[i][0]>=zero)==(p[0]>=zero):
            stride=raw[i][0]-p[0]
            # ndNum stride is uint16 in elements. Split instead of truncating.
            if stride*n<=65535:
                while i<len(raw) and raw[i][1]==p[1] and (raw[i][0]>=zero)==(p[0]>=zero) and raw[i][0]==p[0]+p[2]*stride and raw[i][4]==p[4]+p[2]*p[1]:
                    p[2]+=1;p[3]=stride;i+=1
        out.append(p)
    return out

def original_cora(order:str)->list[list[int]]:
    groups=[[] for _ in range(170)]
    base=BUNDLE/'t8-cpu-prep-20261114'/'prep'/f'cora-A0-W16-{order}'
    for r in csv.DictReader((base/'replay/segtable.csv').open()):
        groups[int(r['window'])]+=range(int(r['seg_start']),int(r['seg_start'])+int(r['seg_len']))
    replay=json.loads((BUNDLE/'t8-m4-replay-20261115'/f'{order}-rows.json').read_text())
    assert groups==replay
    summary=json.loads((base/'summary.json').read_text())
    assert sum(map(len,groups))==summary['sumU']
    assert sum(len(pieces(x)) for x in groups)==summary['sumR']
    return groups

def cpu_layout(rows:list[int],n:int,es:int)->dict:
    """Independent per-element golden vs DMA block semantics for both ordinary paths."""
    c0=32//es;gold={};rowcopy={};stripe={}
    for k,r in enumerate(rows):
        for j in range(n):gold[(j//c0)*16*c0+k*c0+j%c0]=(r,j)
    for k,r in enumerate(rows):
        for block in range(n//c0):
            for q in range(c0):rowcopy[k*c0+block*16*c0+q]=(r,block*c0+q)
    for r,h,_,_,k,*_ in pieces(rows):
        for col in range(n//c0):
            for block in range(h):
                for q in range(c0):stripe[col*16*c0+(k+block)*c0+q]=(r+block,col*c0+q)
    assert gold==rowcopy==stripe
    assert len(gold)==len(rows)*n
    return dict(ordinary_row_calls=len(rows),ordinary_stripe_calls=len(pieces(rows))*(n//c0))

def main()->None:
    out=ROOT/'inputs';out.mkdir(exist_ok=True);cases=[];audits=[]
    cora={o:original_cora(o) for o in ['B0','B1']}
    geom={}
    for r in [1,4,16,64]:
        rng=random.Random(20261115+r);rows=[];pos=0
        for _ in range(r):
            rows+=range(pos,pos+64//r);pos+=64//r+rng.randint(1,2)
        geom[f'synthetic-r{r}']=[rows]
    geom.update({f'cora-{o}':v for o,v in cora.items()})
    # Correctness extras exercise tails, zero padding and the legal-stride boundary.
    for h in [1,4,16]:
        geom[f'gate-h{h}']=[list(range(0,h))+list(range(23,23+h))]
    geom['gate-tail']=[list(range(19)),[2,4,9]]
    geom['gate-stride']=[[0,1,2,3,4095,4096,4097,4098,8191,8192,8193,8194,12287,12288,12289,12290]]
    for name,windows in geom.items():
        refs=[];meta=[];flat=[];maxrow=max(max(w) for w in windows)+1
        # Padding uses source zero tail, represented as UINT32_MAX - i in canonical reference.
        for w,rows in enumerate(windows):
            for ti in range((len(rows)+15)//16):
                chunk=rows[ti*16:ti*16+16];refs+=chunk+[0xffffffff-i for i in range(16-len(chunk))]
                meta += [w,ti,int((ti+1)*16>=len(rows))]
        for dtype,es in [('FP16',2),('FP32',4)]:
          for n in [16,128,256]:
            # Keep the all-zero padding source separate from the logical B rows.
            physical=[r if r<0xffffff00 else maxrow+16+0xffffffff-r for r in refs]
            cmd=[];offset=[0];perpath=[0,0,0]
            for ti in range(len(meta)//3):
                rr=physical[ti*16:ti*16+16];cc=commands(rr,n,maxrow)
                cmd+=cc;offset.append(len(cmd));audit=cpu_layout(rr,n,es)
                perpath[0]+=len(cc);perpath[1]+=audit['ordinary_row_calls'];perpath[2]+=audit['ordinary_stripe_calls']
                # Simulate ND2NZ address mapping separately against raw selected rows.
                decoded=[None]*16
                for row,h,s,stride,k,*_ in cc:
                    assert s==1 or stride*n<=65535
                    for m in range(s):
                        for q in range(h):
                            assert decoded[k+m*h+q] is None
                            decoded[k+m*h+q]=row+m*stride+q
                assert decoded==rr
            audits.append(dict(geometry=name,dtype=dtype,n=n,tiles=len(meta)//3,window_count=len(windows),sumU=sum(map(len,windows)),originalR=sum(len(pieces(w)) for w in windows),calls=perpath))
            for cache in (['hot','cold'] if not name.startswith('gate') else ['hot']):
              for path in range(3):
                # Match the M4 capacity gmax, common to every B path.
                g=(524032//(2*16*n*es))//2*2
                title=f'{name}-{dtype}-n{n}-{cache}-p{path}'
                cfg=[int(es==4),n,len(meta)//3,g,0,0,24,1,path,len(windows),maxrow,0,maxrow,0,0,0,0,perpath[path],int(cache=='cold'),0,0,0,0,0]+meta+physical
                put(out/(title+'.config.bin'),cfg);put(out/(title+'.commands.bin'),[v for c in cmd for v in c]);put(out/(title+'.offsets.bin'),offset)
                # Independent logical rows are sent to host reference; never decode DMA commands there.
                put(out/(title+'.rows.bin'),refs);put(out/(title+'.lengths.bin'),list(map(len,windows)))
                cases.append(dict(name=title,geometry=name,dtype=dtype,n=n,cache=cache,path=path,tiles=len(meta)//3,g=g,sumU=sum(map(len,windows)),source_span_rows=maxrow,calls=perpath[path],gate_only=name.startswith('gate')))
    (ROOT/'manifest.json').write_text(json.dumps(cases,indent=2))
    (ROOT/'cpu-address-audit.json').write_text(json.dumps(dict(status='PASS',cora={o:dict(windows=len(v),sumU=sum(map(len,v)),sumR=sum(len(pieces(w)) for w in v)) for o,v in cora.items()},points=audits),indent=2))
    for kind,predicate in [('all',lambda c:True),('gate',lambda c:c['cache']=='hot'),('stage3',lambda c:not c['gate_only'])]:
        (ROOT/f'{kind}.list').write_text('\n'.join(c['name'] for c in cases if predicate(c))+'\n')
    checks={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.bin')}
    (ROOT/'input-sha256.json').write_text(json.dumps(checks,indent=2))
    print(json.dumps(dict(status='PASS',cases=len(cases),cpu_layout_points=len(audits),cora=json.loads((ROOT/'cpu-address-audit.json').read_text())['cora'])))
if __name__=='__main__':main()
