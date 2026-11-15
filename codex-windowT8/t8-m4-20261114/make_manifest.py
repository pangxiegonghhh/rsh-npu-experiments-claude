"""Register M4 geometries and the exact per-16-row DMA command tables."""
import json, hashlib, struct
from pathlib import Path

def table(u,r,gap,skew,merge):
    lengths=[u-r+1]+[1]*(r-1) if skew else [u//r]*r
    segments=[];src=dst=0
    for h in lengths:
        segments.append((src,dst,h));src+=h+gap;dst+=h
    commands=[];offsets=[0]
    for tile in range(u//16):
        pieces=[]
        for start,logical,h in segments:
            lo=max(tile*16,logical);hi=min(tile*16+16,logical+h)
            if hi>lo:pieces.append([start+lo-logical,hi-lo,1,0,lo-tile*16])
        if merge:
            packed=[];i=0
            while i<len(pieces):
                cmd=pieces[i].copy();i+=1
                if i<len(pieces) and pieces[i][1]==cmd[1]:
                    stride=pieces[i][0]-cmd[0]
                    while i<len(pieces) and pieces[i][1]==cmd[1] and pieces[i][0]==cmd[0]+cmd[2]*stride and pieces[i][4]==cmd[4]+cmd[2]*cmd[1]:
                        cmd[2]+=1;cmd[3]=stride;i+=1
                packed.append(cmd)
            pieces=packed
        commands.extend(x+[0,0,0] for x in pieces);offsets.append(len(commands))
    assert sum(c[1]*c[2] for c in commands)==u
    return commands,offsets,lengths

def main():
    geometries=[]
    for n in [16,32,64,128,256]:
        for r in [1,2,4,8,16,32,64]:
            for gap in [2,64]:geometries.append(('core',64,r,n,gap,False))
    for u in [32,128,256]:
        for n in [16,128]:
            for k in range(u.bit_length()):geometries.append(('extended',u,2**k,n,2,False))
    for n in [16,128]:
        for r in [8,16,32]:geometries.append(('skew',64,r,n,2,True))
    # U=64 alone cannot identify both an intercept and the byte coefficient.
    # Add the minimum U controls for N values missing the draft's extension.
    for n in [32,64,256]:
        for u in [32,128,256]:
            for r in [1,16]:geometries.append(('identify',u,r,n,2,False))
    rows=[];seen={}
    for family,u,r,n,gap,skew in geometries:
      for dtype,es in [('FP16',2),('FP32',4)]:
       for cache in ['hot','cold']:
        for merge in [False,True]:
         cmds,offsets,lengths=table(u,r,gap,skew,merge)
         for pipeline in ['serial','g2','gmax']:
          maxg=int(524032//(2*16*n*es));maxg-=maxg%2
          g=1 if pipeline=='serial' else 2 if pipeline=='g2' else maxg
          name=f'{family}-u{u}-r{r}-n{n}-{dtype}-{cache}-gap{gap}-'+('merge' if merge else 'split')+'-'+pipeline
          pool=64*1024**2 if cache=='hot' else 2*1024**3
          poolrows=pool//(n*es);span=u+(r-1)*gap;h=u//r
          interleave=not skew and gap%h==0
          lanes=(h+gap)//h if interleave else 1
          physical_windows=(poolrows//(r*(h+gap)))*lanes if interleave else poolrows//span
          capacity_windows=physical_windows
          target_working_bytes=32*1024**2 if cache=='hot' else 1024**3
          physical_windows=target_working_bytes//(u*n*es)
          assert physical_windows<=capacity_windows
          unique_bytes=physical_windows*u*n*es
          assert cache!='cold' or unique_bytes>=4*201326592
          row=dict(name=name,family=family,u=u,r=r,n=n,dtype=dtype,element_bytes=es,cache=cache,gap=gap,skew=skew,merge=merge,pipeline=pipeline,g=g,gmax=maxg,pool_bytes=pool,interleave=interleave,lanes=lanes,span_rows=span,physical_windows=physical_windows,unique_useful_working_set_bytes=unique_bytes,commands=cmds,offsets=offsets,commands_per_window=len(cmds),lengths=lengths)
          # For serial/merged aliases the binary, command bytes and address schedule
          # must all match. Preserve logical rows even when no second run is needed.
          key=json.dumps({k:row[k] for k in ['u','n','dtype','cache','g','pipeline','interleave','lanes','span_rows','physical_windows','commands','offsets']},sort_keys=True)
          digest=hashlib.sha256(key.encode()).hexdigest()
          if digest in seen:row['alias_of']=seen[digest]
          else:seen[digest]=name
          rows.append(row)
    Path('m4-manifest.json').write_text(json.dumps(rows,indent=2))
    inputs=Path('inputs');inputs.mkdir(exist_ok=True)
    names=[]
    for row in rows:
      if 'alias_of' in row:continue
      name=row['name'];names.append(name)
      cfg=[int(row['dtype']=='FP32'),row['n'],row['u'],row['g'],int(row['pipeline']=='serial'),0,0,0,row['commands_per_window'],int(row['cache']=='cold'),row['r'],row['gap'],int(row['interleave']),row['lanes'],row['span_rows'],row['physical_windows'],row['u']//row['r'],row['r']*(row['u']//row['r']+row['gap']),int(row['skew'])]
      (inputs/(name+'.config.bin')).write_bytes(struct.pack('<'+str(len(cfg))+'I',*cfg))
      flat=[x for cmd in row['commands'] for x in cmd]
      (inputs/(name+'.commands.bin')).write_bytes(struct.pack('<'+str(len(flat))+'I',*flat))
      (inputs/(name+'.offsets.bin')).write_bytes(struct.pack('<'+str(len(row['offsets']))+'I',*row['offsets']))
    Path('cases.list').write_text('\n'.join(names)+'\n')
    print(json.dumps(dict(logical_points=len(rows),unique_runs=len(seen),aliases=len(rows)-len(seen),base_design_points=len(geometries)*4)))

if __name__=='__main__':main()
