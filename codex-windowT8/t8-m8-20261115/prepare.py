"""Generate M8 independent row lists and legal per-tile ND2NZ commands, offline."""
from pathlib import Path
import json,struct,hashlib,shutil
ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
def binary(path,values):path.write_bytes(struct.pack('<%dI'%len(values),*values))
def commands(rows,merge,n):
    pieces=[];i=0
    while i<16:
        j=i+1
        while j<16 and rows[i]!=0xffffffff and rows[j]==rows[j-1]+1:j+=1
        # zero source row is replicated, never copied as a contiguous run.
        pieces.append([rows[i],j-i,1,0,i,0,0,0]);i=j
    if merge:
        packed=[];i=0
        while i<len(pieces):
            p=pieces[i].copy();i+=1
            if i<len(pieces) and p[0]!=0xffffffff and pieces[i][0]!=0xffffffff:
                stride=pieces[i][0]-p[0]
                if 0<stride*n<=65535:
                    while i<len(pieces) and pieces[i][1]==p[1] and pieces[i][0]==p[0]+p[2]*stride and pieces[i][4]==p[4]+p[2]*p[1]:
                        p[2]+=1;p[3]=stride;i+=1
            packed.append(p)
        pieces=packed
    rebuilt=[None]*16
    for row,h,count,stride,k,*_ in pieces:
        assert count<=16 and (count==1 or stride*n<=65535)
        for q in range(count):
            for j in range(h):
                dst=k+q*h+j;assert rebuilt[dst] is None
                rebuilt[dst]=row if row==0xffffffff else row+q*stride+j
    assert rebuilt==rows
    return pieces
def main():
    inp=ROOT/'inputs';inp.mkdir(exist_ok=True)
    geometry=[]
    for u,rs in [(16,[1,4,16]),(64,[1,4,16,64]),(256,[1,4,16,64,256])]:
        for r in rs:
            h=u//r;rows=[s*(h+2)+j for s in range(r) for j in range(h)]
            geometry.append((f'u{u}-r{r}',[rows],u+(r-1)*2,r))
    for order in ['B0','B1']:
        source=ROOT/'sources'/f'{order}-rows.json'
        if not source.exists():source=PARENT/'t8-m4-replay-20261115'/f'{order}-rows.json'
        rows=json.loads(source.read_text())
        assert len(rows)==170
        geometry.append((f'cora-{order}',rows,2708,None))
    manifest=[]
    for tag,windows,span,r in geometry:
      for dt,es in [(0,2),(1,4)]:
       for n in [16,32,64,128,256]:
        for cold in [0,1]:
         u=sum(map(len,windows));r_total=sum(sum(i==0 or rr[i]!=rr[i-1]+1 for i in range(len(rr))) for rr in windows)
         h=len(windows[0])//r if r else 0
         interleave=int(r is not None and 2%h==0);lanes=(h+2)//h if interleave else 1
         stride=r*(h+2) if interleave else span
         pool=2*1024**3;working=(1024 if cold else 32)*1024**2
         physical=working//(u*n*es) if r else working//(2708*n*es)
         assert physical>0
         # Exactly disjoint row sets for synthetic windows, with shared gap lanes only when legal.
         if r:
             rowset=set()
             for index in range(min(physical,256)):
                 base=(index//lanes)*stride+(index%lanes)*h if interleave else index*span
                 rr={base+q for q in windows[0]};assert not rowset.intersection(rr);rowset.update(rr)
             last=(physical-1)//lanes*stride+(physical-1)%lanes*h if interleave else (physical-1)*span
             assert (last+span+1)*n*es<pool
             unique_bytes=physical*u*n*es
         else:
             unique_bytes=physical*len(set(q for w in windows for q in w))*n*es
             assert (physical*2708+1)*n*es<pool
         assert not cold or unique_bytes>4*201326592
         for path in [0,1,2]:
             name=f'{tag}-n{n}-'+('FP32' if dt else 'FP16')+'-'+('cold' if cold else 'hot')+'-'+['split','merge','pack'][path]
             cmds=[];off=[0];rr=[];wm=[]
             for w in windows:
                 first=len(off)-1;tiles=(len(w)+15)//16;wm.extend([first,tiles,len(w),sum(i==0 or w[i]!=w[i-1]+1 for i in range(len(w)))])
                 for t in range(tiles):
                     tile=w[t*16:t*16+16]+[0xffffffff]*max(0,(t+1)*16-len(w))
                     rr.extend(tile);cmds.extend(commands(tile,path==1,n));off.append(len(cmds))
             cfg=[dt,n,path,0,0,24,len(off)-1,len(windows),max(wm[i+1] for i in range(0,len(wm),4)),cold,span,physical,interleave,lanes,stride,h,physical if not r else 0,int(r is None),0]
             for suffix,v in [('config',cfg),('commands',[q for c in cmds for q in c]),('offsets',off),('rows',rr),('windows',wm)]:binary(inp/(name+'.'+suffix+'.bin'),v)
             manifest.append(dict(name=name,tag=tag,dtype=dt,n=n,cache='cold' if cold else 'hot',path=['split','merge','pack'][path],u=u,r=r_total,window_count=len(windows),max_tiles=cfg[8],commands=len(cmds),packed_rows=16*(len(off)-1),unique_input_bytes=unique_bytes,pool_bytes=pool,ring_bytes=24*cfg[8]*16*n*es,physical_instances=physical,span=span,rows=windows))
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (ROOT/'cases.list').write_text('\n'.join(x['name'] for x in manifest)+'\n')
    # A small first gate includes both precisions, extreme feature dimensions, both ring stress and tails.
    first=[x['name'] for x in manifest if x['tag'] in ['u16-r16','u256-r1','u256-r256','cora-B1'] and x['n'] in [16,256] and x['cache']=='hot']
    (ROOT/'first.list').write_text('\n'.join(first)+'\n')
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inp.iterdir())}
    (ROOT/'input-hashes.json').write_text(json.dumps(hashes,indent=2))
    if not (ROOT/'CMakeLists.txt').exists():shutil.copyfile(PARENT/'t8-m4-20261114/CMakeLists.txt',ROOT/'CMakeLists.txt')
    print(json.dumps(dict(points=len(manifest),synthetic=720,cora=120,first=len(first),input_files=len(hashes))))
if __name__=='__main__':main()
