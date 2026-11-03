"""E0 deterministic input, independent output checker and recorded device driver.
Prepare/selfcheck are CPU-only. run invokes only explicit E0 probe executables.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np


def write_json(p: Path, value: object) -> None:
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def check_guard(raw: bytes, size: int, guard_byte: int = 0x5a) -> int:
    if len(raw) != size + 2048:
        raise ValueError('readback size mismatch')
    return sum(x != guard_byte for x in raw[:1024] + raw[-1024:])


def check_output(raw: bytes, expected: np.ndarray, mask: np.ndarray, guard_byte: int = 0x5a) -> dict:
    guards = check_guard(raw, expected.nbytes, guard_byte)
    x = np.frombuffer(raw[1024:-1024], dtype='<f4').reshape(expected.shape)
    err = np.abs(x.astype(np.float64)-expected.astype(np.float64))
    bad = (~np.isfinite(x) | (err != 0)) & mask
    return {'max_abs_error': float(err[mask].max(initial=0)),
            'value_errors': int(bad.sum()), 'guard_errors': guards,
            'first_bad': np.argwhere(bad)[:5].tolist()}


def make_case(root: Path, name: str, a: np.ndarray, dense_b: np.ndarray,
              *, k: int, n: int, layout: int = 1, split: int = 0,
              compact: int = 0, bulk: int = 1, bbulk: int = 1,
              logical: int = 0, mapping: str = 'scatter', stage: str = 'S3',
              tags: dict | None = None) -> dict:
    a = a.astype('<f2');dense_b = dense_b.astype('<f2')
    mp, kp = a.shape; npad = dense_b.shape[1]
    if mapping == 'scatter': rows = np.arange(kp,dtype=np.int32)*3+1
    elif mapping == 'segments': rows = np.where(np.arange(kp)<16,np.arange(kp)+2,np.arange(kp)+35).astype(np.int32)
    else: rows = np.arange(kp,dtype=np.int32)
    global_k = int(rows.max())+1
    # Unmapped original B rows are nonzero so using local instead of global indices fails.
    b = np.full((global_k+1,npad),np.float16(3/8),dtype='<f2')
    b[rows] = dense_b
    b[-1] = 0
    refs = rows.copy()
    # Each layout diagnostic can intentionally supply nonzero padded basis rows.
    # The caller owns the exact padded matrix and expected result.
    config=np.array([mp if not logical else 30,k,n,mp,kp,npad,layout,split,compact,bulk,logical,bbulk],dtype='<i4')
    if tags and 'm' in tags: config[0]=tags['m']
    output = (a.astype(np.float64) @ dense_b.astype(np.float64)).astype('<f4')
    # Independent scalar logical reference. No use of device address helper or packing code.
    if logical:
        output[:config[0],:n] = (a[:config[0],:k].astype(np.float64) @ dense_b[:k,:n].astype(np.float64)).astype('<f4')
    mask=np.ones(output.shape,dtype=np.uint8)
    if logical: mask[:]=0;mask[:config[0],:n]=1
    p=root/name;p.mkdir(parents=True,exist_ok=True)
    source=a[:,:compact] if compact else a
    source.tofile(p/'a.bin')
    # Direct A fixture: explicit scalar slot enumeration, independent of normal ND2NZ.
    direct=np.zeros(mp*kp,dtype='<f2')
    for r in range(mp):
        for j in range(kp):
            off=(r//16)*(kp//16)*256+(j//16)*256+(r%16)*16+j%16
            direct[off]=a[r,j]
    direct.tofile(p/'a-direct.bin');b.tofile(p/'b.bin');refs.tofile(p/'refs.bin')
    config.tofile(p/'config.bin');output.tofile(p/'golden.bin');mask.tofile(p/'mask.bin')
    info={'id':name,'stage':stage,'config':config.tolist(),'global_k':global_k,
          'observation':'selector_observed' if 'selector' in name else 'product',
          'mapping':mapping,'tags':tags or {},'guard_bytes':1024,
          'a_source_elements':source.size,'a_l1_elements':mp*kp,
          'b_source_rows':global_k+1,'b_l1_elements':kp*npad,
          'mmad_calls':kp//16 if split else 1,
          'expected_mmad':[int(config[0]) if logical else mp,16 if split else (k if logical else kp),n if logical else npad]}
    # Enumerate source row transfer intervals, reject before a kernel sees them.
    intervals=[(int(r)*npad*2,(int(r)+1)*npad*2) for r in refs]
    assert min(lo for lo,_ in intervals)>=0 and max(hi for _,hi in intervals)<=b.nbytes
    info['read_range_check']={'pass':True,'b_intervals_bytes':intervals,'a_nd_bytes':source.nbytes,
                              'a_physical_bytes':a.nbytes,'refs_bytes':refs.nbytes}
    info['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('*.bin')}
    write_json(p/'case.json',info)
    return info


def values(m: int,k: int,n: int) -> tuple[np.ndarray,np.ndarray]:
    a=np.fromfunction(lambda r,c:((r*11+c*7)%17-8)/8,(m,k)).astype('<f2')
    b=np.fromfunction(lambda r,c:((r*13+c*5)%19-9)/8,(k,n)).astype('<f2')
    return a,b


def prepare(root: Path) -> None:
    root.mkdir(parents=True,exist_ok=True);cases=[]
    def add(name: str,a: np.ndarray,b: np.ndarray,**kw: object) -> None:
        cases.append(make_case(root,name,a,b,**kw))
    for k,n in [(16,16),(32,33),(48,64),(17,17)]:
        kp=(k+15)//16*16;npad=(n+15)//16*16;a,b=values(16,kp,npad)
        a[:,k:]=0;b[k:]=0;b[:,n:]=0
        add(f'control_K{k}_N{n}',a,b,k=k,n=n,stage='S2',split=1)
    for kp in (16,32,48):
        for bulk in (0,1):
            for label in ('tile','element'):
                a=np.fromfunction((lambda r,c:c//16+1) if label=='tile' else (lambda r,c:16*r+c%16+1),(16,kp)).astype('<f2')
                for selected in range(kp//16):
                    b=np.zeros((kp,16),dtype='<f2');b[selected*16:(selected+1)*16]=np.eye(16,dtype='<f2')
                    add(f'A-selector_K{kp}_bulk{bulk}_{label}_s{selected}',a,b,k=kp,n=16,bulk=bulk)
        for npad in (16,32,64):
            for layout in (0,1):
                for bbulk in (0,1):
                    for label in ('tile','element'):
                        b=np.fromfunction((lambda r,c:(r//16)*(npad//16)+c//16+1) if label=='tile' else (lambda r,c:16*(r%16)+c%16+1),(kp,npad)).astype('<f2')
                        for selected in range(kp//16):
                            a=np.zeros((16,kp),dtype='<f2');a[:,selected*16:(selected+1)*16]=np.eye(16,dtype='<f2')
                            add(f'B-selector_K{kp}_N{npad}_l{layout}_b{bbulk}_{label}_s{selected}',a,b,k=kp,n=npad,layout=layout,bbulk=bbulk)
    for mapping in ('continuous','scatter','segments'):
        a,b=values(16,32,48);b[:,33:]=0
        add(f'mapping_{mapping}',a,b,k=32,n=33,mapping=mapping)
    for k in (16,32,48):
        for n in (17,33):
            a,b=values(16,k,(n+15)//16*16);b[:,n:]=0
            add(f'N-tail_K{k}_N{n}',a,b,k=k,n=n,split=1,stage='S4')
    for k,n in [(1,17),(5,17),(15,17),(17,17),(17,33),(31,33),(37,33)]:
        kp=(k+15)//16*16;npad=(n+15)//16*16;a,b=values(16,kp,npad)
        a[:,k:]=0;b[k:]=0;b[:,n:]=0
        add(f'K-tail_K{k}_N{n}',a,b,k=k,n=n,split=1,stage='S4')
    for valid in (1,5,15):
        a,_=values(16,16,16);a[:,valid:]=0;b=np.eye(16,dtype='<f2')
        add(f'compact-A-selector_v{valid}',a,b,k=16,n=16,compact=valid,stage='S4')
        add(f'dense-A-selector_v{valid}',a,b,k=16,n=16,stage='S4')
    for k,n in ((32,32),(48,64)):
        a,b=values(16,k,n)
        for split in (0,1):add(f'logical_K{k}_N{n}_split{split}',a,b,k=k,n=n,split=split,stage='S5')
    a,b=values(32,80,48);a[30:]=0;a[:,70:]=0;b[70:]=0;b[:,40:]=0
    add('logical_M30_K70_N40',a,b,k=70,n=40,logical=1,stage='S5')
    # Non-symmetric outer products at locations spanning both M and N fractals.
    for r,c in ((0,0),(15,15),(16,16),(29,39)):
        a=np.zeros((32,16),dtype='<f2');b=np.zeros((16,48),dtype='<f2')
        a[r,3]=1;b[3,c]=7
        add(f'writeback_r{r}_c{c}',a,b,k=16,n=48,stage='S1')
    for valid in (1,5,15,17,31,37):
        kp=(valid+15)//16*16
        for selected in range(kp//16):
            a,_=values(16,kp,16);a[:,valid:]=0
            selector=np.zeros((kp,16),dtype='<f2');selector[selected*16:(selected+1)*16]=np.eye(16,dtype='<f2')
            add(f'tail-A-selector_K{valid}_s{selected}',a,selector,k=kp,n=16,stage='S4-extra')
            _,b=values(16,kp,48);b[valid:]=0;b[:,33:]=0
            a=np.zeros((16,kp),dtype='<f2');a[:,selected*16:(selected+1)*16]=np.eye(16,dtype='<f2')
            add(f'tail-B-selector_K{valid}_s{selected}',a,b,k=kp,n=48,stage='S4-extra')
    write_json(root/'manifest.json',{'schema':'e0-supplement-v1','cases':cases})
    print('prepared',len(cases),'cases')


def validate(case: Path, output: Path, direct: bool=False) -> dict:
    info=json.loads((case/'case.json').read_text());c=info['config'];shape=(c[3],c[5])
    expected=np.fromfile(case/'golden.bin',dtype='<f4').reshape(shape)
    mask=np.fromfile(case/'mask.bin',dtype=np.uint8).reshape(shape).astype(bool)
    checks=[];errors=0
    guard_byte=json.loads((output/'host.json').read_text()).get('guard_byte',0x5a)
    outputs=sorted(output.glob('output-*.bin'),key=lambda p:int(p.stem.split('-')[-1]))
    for p in outputs:
        iteration=int(p.stem.split('-')[-1]);ref=expected if (iteration%2+(iteration//2)%2)%2==0 else -expected
        ck=check_output(p.read_bytes(),ref,mask,guard_byte)
        dbgraw=(output/f'debug-{iteration}.bin').read_bytes();ck['debug_guard_errors']=check_guard(dbgraw,16,guard_byte)
        debug=np.frombuffer(dbgraw[1024:-1024],dtype='<i4').tolist()
        ck['debug']=debug;ck['call_params_correct']=debug==[info['mmad_calls'],*info['expected_mmad']]
        ck['padding_errors']=None if c[10] else int(np.count_nonzero(np.frombuffer(p.read_bytes()[1024:-1024],dtype='<f4').reshape(shape)[expected==0]))
        errors+=ck['value_errors']+ck['guard_errors']+ck['debug_guard_errors']+int(not ck['call_params_correct'])
        checks.append(ck)
    sources={}
    for key in ('a','b','refs','config'):
        original=(case/('a-direct.bin' if key=='a' and direct else key+'.bin')).read_bytes()
        if outputs and ((key=='b' and (len(outputs)-1)%2) or (key=='a' and ((len(outputs)-1)//2)%2)):
            x=np.frombuffer(original,dtype='<u2').copy();x^=0x8000;original=x.tobytes()
        raw=(output/(key+'-after.bin')).read_bytes()
        g=check_guard(raw,len(original),guard_byte);same=raw[1024:-1024]==original
        sources[key]={'guard_errors':g,'payload_unchanged':same};errors+=g+int(not same)
    if not outputs:errors+=1
    result={'case_id':info['id'],'stage':info['stage'],'status':'PASS' if errors==0 else 'FAIL',
            'path':'direct' if direct else 'normal','iterations':len(outputs),'checks':checks,'sources':sources,
            'read_range_check':info['read_range_check']['pass'],'observation_method':info['observation'],
            'max_abs_error':max((x['max_abs_error'] for x in checks),default=None)}
    write_json(output/'check.json',result);return result


def selfcheck() -> None:
    e=np.arange(512,dtype='<f4').reshape(16,32)+1;mask=np.ones(e.shape,dtype=bool)
    raw=bytes([0x5a])*1024+e.tobytes()+bytes([0x5a])*1024
    assert check_output(raw,e,mask)['value_errors']==0
    x=e.copy();x[:,[0,16]]=x[:,[16,0]]
    assert check_output(raw,x,mask)['value_errors']>0
    x=e.copy();x[:,:16]=x[:,:16].T
    assert check_output(raw,x,mask)['value_errors']>0
    corrupt=bytearray(raw);corrupt[0]^=1
    assert check_output(bytes(corrupt),e,mask)['guard_errors']==1
    x=e.copy();x[0,0]=0;assert check_output(raw,x,mask)['value_errors']==1
    def valid_ref(row: int,rows: int) -> bool:return 0<=row<rows
    assert not valid_ref(-1,16) and not valid_ref(16,16)
    print('PASS checker mutation selfcheck: block swap, transpose, value/padding, guard, invalid index')


def run(cases: Path, build: Path, out: Path, select: str, mode: str, iterations: int) -> None:
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((cases/'manifest.json').read_text())
    records=[]
    for case in manifest['cases']:
        if select not in ('all',case['stage']) and select not in case['id']:continue
        dst=out/case['id'];dst.mkdir(parents=True,exist_ok=True)
        cmd=[str(build/f'e0_{mode}'),str(cases/case['id']),str(dst),'direct' if mode=='direct' else 'normal',str(iterations)]
        with (out/'commands.txt').open('a') as f:f.write(json.dumps(cmd)+'\n')
        started=time.time()
        try:
            p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
            (dst/'run.log').write_bytes(p.stdout)
            result=validate(cases/case['id'],dst,mode=='direct') if p.returncode==0 else {'status':'FAIL','returncode':p.returncode,'case_id':case['id']}
        except subprocess.TimeoutExpired as exc:
            (dst/'run.log').write_bytes(exc.stdout or b'');result={'status':'TIMEOUT','case_id':case['id']}
        result['elapsed_s']=time.time()-started;records.append(result)
        write_json(out/'checks.json',records)
        print(result['case_id'],result['status'],flush=True)
        if result['status']!='PASS':break
    if not records:raise ValueError('No matching cases')
    if any(x['status']!='PASS' for x in records):raise SystemExit(1)


def main() -> None:
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('root',type=Path)
    sub.add_parser('selfcheck')
    p=sub.add_parser('run');p.add_argument('cases',type=Path);p.add_argument('build',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--select',default='all');p.add_argument('--mode',choices=('normal','direct','dual'),default='normal');p.add_argument('--iterations',type=int,default=1)
    args=parser.parse_args()
    if args.action=='prepare':prepare(args.root)
    elif args.action=='selfcheck':selfcheck()
    else:run(args.cases,args.build,args.out,args.select,args.mode,args.iterations)

if __name__=='__main__':main()
