"""Build a separate variable-window replay of the registered Cora B0/B1 tables."""
import csv
import json
import shutil
import struct
from pathlib import Path

here=Path(__file__).resolve().parent
out=here.parent/'t8-m4-replay-20261115';out.mkdir(exist_ok=True)
s=(here/'kernel.cpp').read_text()
s=s.replace('uint32_t n,u,g,serial,windows,blocks,capture,commands;','uint32_t n,u,g,serial,windows,blocks,capture,commands,outputWindows,zeroRow;')
s=s.replace('x.u/16','x.u')
s=s.replace('src[uint64_t(base+row)*x.n]','src[uint64_t(cmd.GetValue(c*8+6)?x.zeroRow:base+row)*x.n]')
s=s.replace('const P4&x,uint32_t linear){','const P4&x,uint32_t linear,GlobalTensor<uint32_t>&meta){')
old='uint32_t slot=linear%2,tile=linear%(x.u),window=linear/(x.u)*x.blocks+GetBlockIdx();'
new='uint32_t slot=linear%2,ti=linear%x.u,epoch=linear/x.u,window=meta.GetValue(ti*3),tile=meta.GetValue(ti*3+1),last=meta.GetValue(ti*3+2);'
assert old in s;s=s.replace(old,new)
s=s.replace('x.capture&&tile+1==x.u','x.capture&&last')
s=s.replace('out[uint64_t(window)*16*x.n]','out[(uint64_t(epoch*x.outputWindows+window)*x.blocks+GetBlockIdx())*16*x.n]')
s=s.replace('Run4(GM_ADDR input,','Run4(GM_ADDR config,GM_ADDR input,')
s=s.replace('TPipe pipe;TBuf<TPosition::B1>storage;','GlobalTensor<uint32_t>meta;meta.SetGlobalBuffer((__gm__ uint32_t*)config+24);TPipe pipe;TBuf<TPosition::B1>storage;')
s=s.replace('Compute4(bl,b2,aa,acc,out,x,t);','Compute4(bl,b2,aa,acc,out,x,t,meta);')
s=s.replace('Compute4(bl,b2,aa,acc,out,x,start+i);','Compute4(bl,b2,aa,acc,out,x,start+i,meta);')
s=s.replace('c.GetValue(8)};','c.GetValue(8),c.GetValue(9),c.GetValue(10)};')
s=s.replace('Run4<float>(in,','Run4<float>(config,in,').replace('Run4<half>(in,','Run4<half>(config,in,')
s=s.replace('m4_kernel','replay_kernel')
(out/'kernel.cpp').write_text(s)
shutil.copyfile(here/'CMakeLists.txt',out/'CMakeLists.txt')
base=(here/'host.cpp').read_text().replace('int main(int argc,char**argv)','int synthetic_main_unused(int argc,char**argv)')
(out/'host-base.h').write_text(base)

manifest=[]
for order in ('B0','B1'):
    prep=here.parent/'t8-cpu-prep-20261114'/'prep'/f'cora-A0-W16-{order}'
    segments={}
    for r in csv.DictReader((prep/'replay/segtable.csv').open()):
        segments.setdefault(int(r['window']),[]).append((int(r['seg_start']),int(r['seg_len'])))
    windows=list(csv.DictReader((prep/'windows.csv').open()))
    assert sum(int(r['U']) for r in windows)==(9583 if order=='B0' else 6035)
    assert sum(int(r['R']) for r in windows)==(8565 if order=='B0' else 2927)
    commands=[];offsets=[0];meta=[];reference_rows=[];union=set()
    for w,row in enumerate(windows):
        columns=[c for start,h in segments[w] for c in range(start,start+h)]
        assert len(columns)==int(row['U'])
        union.update(columns);reference_rows.append(columns)
        logical=[];at=0
        for start,h in segments[w]:logical.append((start,at,h));at+=h
        chunks=(len(columns)+15)//16
        for tile in range(chunks):
            pieces=[]
            for start,logical_start,h in logical:
                lo=max(tile*16,logical_start);hi=min(tile*16+16,logical_start+h)
                if hi>lo:pieces.append([start+lo-logical_start,hi-lo,1,0,lo-tile*16,0,0,0])
            grouped=[];i=0
            while i<len(pieces):
                c=pieces[i].copy();i+=1
                if i<len(pieces) and pieces[i][1]==c[1]:
                    step=pieces[i][0]-c[0]
                    while i<len(pieces) and pieces[i][1]==c[1] and pieces[i][0]==c[0]+c[2]*step and pieces[i][4]==c[4]+c[2]*c[1]:
                        c[2]+=1;c[3]=step;i+=1
                grouped.append(c)
            valid=min(16,len(columns)-tile*16)
            if valid<16:grouped.append([0,16-valid,1,0,valid,0,1,0])
            commands.extend(grouped);offsets.append(len(commands));meta.extend([w,tile,int(tile+1==chunks)])
    (out/f'{order}-rows.json').write_text(json.dumps(reference_rows))
    for n in (16,32,64,128,256):
      for dt,es in ((0,2),(1,4)):
       for cold in (0,1):
        name=f'cora-{order}-n{n}-FP{32 if dt else 16}-{"cold" if cold else "hot"}-gmax'
        g=524032//(2*16*n*es);g-=g%2
        target=(1024 if cold else 32)*1024**2
        copies=(target+len(union)*n*es-1)//(len(union)*n*es)
        active=copies*len(union)*n*es
        assert not cold or active>=4*201326592
        legal=[];legal_offsets=[0];split_for_stride=0
        for tile in range(len(meta)//3):
            for c in commands[offsets[tile]:offsets[tile+1]]:
                if c[2]>1 and c[3]*n>65535:
                    split_for_stride+=1
                    for m in range(c[2]):
                        d=c.copy();d[0]+=m*c[3];d[4]+=m*c[1];d[2]=1;d[3]=0;legal.append(d)
                else:legal.append(c)
            legal_offsets.append(len(legal))
        assert all(c[2]==1 or c[3]*n<=65535 for c in legal)
        cfg=[dt,n,len(meta)//3,g,0,0,0,0,len(legal),len(windows),0,cold,copies,2708]+[0]*10+meta
        arrays={'config':cfg,'commands':[v for c in legal for v in c],'offsets':legal_offsets}
        inputs=out/'inputs';inputs.mkdir(exist_ok=True)
        for key,v in arrays.items():(inputs/f'{name}.{key}.bin').write_bytes(struct.pack('<'+str(len(v))+'I',*v))
        manifest.append(dict(name=name,order=order,n=n,dtype=dt,cache='cold' if cold else 'hot',g=g,
                             windows=len(windows),U=sum(map(len,reference_rows)),R=sum(int(r['R']) for r in windows),
                             tiles=len(meta)//3,api_calls=len(legal),zero_pad_commands=sum(c[6] for c in legal),stride_overflow_groups_split=split_for_stride,
                             unique_B_rows=len(union),active_useful_bytes=active,copies=copies,
                             source_rows_per_copy=2708,source_files=str(prep)))
(out/'replay-manifest.json').write_text(json.dumps(manifest,indent=2))
(out/'cases.list').write_text(''.join(r['name']+'\n' for r in manifest))
print(json.dumps(dict(cases=len(manifest),replay_dir=str(out))))
