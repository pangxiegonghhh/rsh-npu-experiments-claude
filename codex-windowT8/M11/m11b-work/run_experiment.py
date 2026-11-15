"""M11b gated execution, complete block records and immutable evidence seal."""
from pathlib import Path
import csv,json,subprocess,hashlib,time,statistics,tarfile,html,os,platform,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def status(state,**kw):
    obj=dict(state=state,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw)
    (ROOT/'live-status.json').write_text(json.dumps(obj,indent=2))
    (ROOT/'live-status.html').write_text('<meta http-equiv="refresh" content="20"><h1>M11b status</h1><pre>'+html.escape(json.dumps(obj,indent=2))+'</pre>')
    print(json.dumps(obj),flush=True)
def run(binary,mode,out,listing,block=0):
    out.mkdir(parents=True,exist_ok=False)
    with (out/'run.log').open('w') as f:
        p=subprocess.run([str(ROOT/'build'/binary),mode,str(out),str(ROOT/listing),str(block),'0'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
    return p.returncode
def validate(out,expected):
    gates=sorted(out.glob('*/gate.json'));assert len(gates)==expected,(str(out),len(gates),expected)
    for g in gates:
        assert json.loads(g.read_text())['status']=='PASS'
        assert (g.parent/'output-f32.bin').read_bytes()==(g.parent/'reference-f32.bin').read_bytes()
    return [dict(case_id=g.parent.name,output_sha256=sha(g.parent/'output-f32.bin')) for g in gates]
def main():
    status('environment')
    env=ROOT/'environment'
    if not env.exists():
        env.mkdir()
        for name,cmd in [('npu-smi',['npu-smi','info']),('compiler',['c++','--version']),('memory',['free','-h'])]:
            q=subprocess.run(cmd,capture_output=True,text=True);(env/(name+'.txt')).write_text(q.stdout+q.stderr)
        (env/'runtime.json').write_text(json.dumps(dict(ASCEND_HOME_PATH=os.environ.get('ASCEND_HOME_PATH'),machine=platform.machine(),utc=time.time()),indent=2))
        sdk=Path(os.environ['ASCEND_HOME_PATH'])
        found=[]
        for pattern in ['kernel_struct_data_copy.h','kernel_struct_mm.h','kernel_operator_transpose_intf.h','kernel_operator_transpose_impl.h']:
            for p in sdk.rglob(pattern):
                if 'aarch64-linux/asc/include' in str(p):
                    target=env/(str(len(found))+'-'+p.name);shutil.copyfile(p,target);found.append(dict(source=str(p),saved=target.name,sha256=sha(target)))
        (env/'sdk-files.json').write_text(json.dumps(found,indent=2))
    original_kernel='63194374d72de61c0bded87ef407d252bb3c3e3519f1d21cd8e242b3242f34b0'
    assert sha(ROOT/'src/kernel.cpp')==original_kernel
    binaries={name:sha(ROOT/'build'/name) for name in ['t8_micro','t8_identity','m11b_b3_gate']}
    gates={}
    for label,binary,listing in [('standard','t8_micro','gate.list'),('strong-address','t8_identity','strong-gate.list')]:
        status('correctness-before-timing',gate=label)
        folder=ROOT/('gate-'+label)
        if not folder.exists():assert run(binary,'check',folder,listing)==0
        gates[label]=validate(folder,84)
    gatefile=ROOT/'GATES-BEFORE-TIMING.json'
    if gatefile.exists():
        registered=json.loads(gatefile.read_text());assert registered['status']=='PASS' and registered['binary_sha256']==binaries and registered['checks']==gates
    else:gatefile.write_text(json.dumps(dict(status='PASS',kernel_sha256=original_kernel,binary_sha256=binaries,utc=time.time(),checks=gates),indent=2))
    status('B3-direct-load-correctness-before-timing')
    b3=[]
    for label,listing in [('transpose','b3-transpose.list'),('plain-only','b3-plain.list')]:
        folder=ROOT/f'gate-B3-{label}'
        if not folder.exists():rc=run('m11b_b3_gate','check',folder,listing)
        else:rc=0 if label=='transpose' else 1
        names=(ROOT/listing).read_text().splitlines()
        for name in names:
            d=folder/name;good=(d/'gate.json').exists();bad=(d/'failure.txt').exists();assert good!=bad,(label,name)
            b3.append(dict(case_id=name,variant=label,status='PASS' if good else 'FAIL',failure=(d/'failure.txt').read_text() if bad else '',output_saved=(d/'output-f32.bin').exists(),output_sha256=sha(d/'output-f32.bin') if (d/'output-f32.bin').exists() else '',process_returncode=rc))
        if label=='transpose':assert rc==0 and len(validate(folder,50))==50
    (ROOT/'B3-GATE-RESULTS.json').write_text(json.dumps(dict(records=b3,formal_timing='NOT_STARTED: equivalence of baseline required',note='plain+explicit unsupported at L0B by documented vector Transpose TPosition; no invalid API executed'),indent=2))
    status('B2-timing',accepted=0,total=20)
    results=ROOT/'results-B2';results.mkdir(exist_ok=True);attempts=json.loads((results/'attempt-registration.json').read_text()) if (results/'attempt-registration.json').exists() else []
    for block in range(20):
        if (results/f'b{block:02}-accepted.json').exists():continue
        accepted=None
        for attempt in range(3):
            folder=results/f'b{block:02}-attempt{attempt}';start=time.time();recovered=folder.exists()
            if not recovered:rc=run('t8_micro','timeblock',folder,'stage3.list',block)
            else:
                assert 'M11_ALL_PASS 84' in (folder/'run.log').read_text();rc=0
            if rc:raise RuntimeError('B2 case failure; preserve '+str(folder))
            rows=list(csv.DictReader((folder/'timing.csv').open()));assert len(rows)==84 and len({r['case'] for r in rows})==84
            groups=list(csv.DictReader((folder/'group-registration.csv').open()));sent=list(csv.DictReader((folder/'sentinel-values.csv').open()));assert len(groups)==4 and len(sent)==40
            for group in groups:
                for position in ['before','after']:
                    vals=[float(r['us']) for r in sent if r['dtype']==group['dtype'] and r['N']==group['N'] and r['position']==position];assert len(vals)==5
                    assert abs(statistics.median(vals)-float(group[position+'_us'])) <= max(1e-4,abs(statistics.median(vals))*5e-6)
                    group[position+'_us_full_precision']=statistics.median(vals)
                group['drift_from_raw5']=abs(group['after_us_full_precision']-group['before_us_full_precision'])/group['before_us_full_precision']
                assert (group['drift_from_raw5']<=.05)==(group['valid']=='1')
            item=dict(block=block,attempt=attempt,recovered_postprocess_validation=recovered,path=str(folder.relative_to(ROOT)),elapsed_s=time.time()-start,groups=groups,valid=all(g['valid']=='1' and g['input_immutable']=='1' for g in groups))
            attempts.append(item);(results/'attempt-registration.json').write_text(json.dumps(attempts,indent=2))
            if item['valid']:accepted=item;break
        assert accepted,'three drift-invalid attempts'
        (results/f'b{block:02}-accepted.json').write_text(json.dumps(accepted,indent=2))
        status('B2-timing',accepted=block+1,total=20,last_block_seconds=accepted['elapsed_s'],invalid_attempts=sum(not r['valid'] for r in attempts))
    assert all(sha(ROOT/'build'/name)==digest for name,digest in binaries.items())
    (ROOT/'formal.rc').write_text('0\n')
    q=subprocess.run(['npu-smi','info'],capture_output=True,text=True);(ROOT/'environment-end-npu-smi.txt').write_text(q.stdout+q.stderr)
    status('sealing',accepted=20)
    archive=ROOT/'m11b-evidence-complete.tar.gz'
    files=[p for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink() and p.name not in ['m11b-evidence-complete.tar.gz','archive-receipt.json','driver.log','live-status.html','live-status.json','EVIDENCE-SHA256.json']]
    manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
    (ROOT/'EVIDENCE-SHA256.json').write_text(json.dumps(manifest,indent=2));files.append(ROOT/'EVIDENCE-SHA256.json')
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(files):tar.add(p,arcname=p.relative_to(ROOT),recursive=False)
    receipt=dict(status='SEALED',archive=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),files=len(files),formal_rc=0)
    (ROOT/'archive-receipt.json').write_text(json.dumps(receipt,indent=2))
    status('SEALED',**{k:v for k,v in receipt.items() if k!='status'})
if __name__=='__main__':
    try:main()
    except Exception as error:
        (ROOT/'failure.txt').write_text(repr(error));status('FAILED',error=repr(error));raise
