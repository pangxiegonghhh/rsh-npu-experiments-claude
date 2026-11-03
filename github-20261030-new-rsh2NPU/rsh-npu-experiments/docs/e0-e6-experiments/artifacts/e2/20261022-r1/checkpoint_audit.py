from pathlib import Path
import json,hashlib,struct
root=Path('/Users/Zhuanz/Documents/ChatGPT/RSH迁移NPU实验');b=root/'docs/e0-e6-experiments/artifacts/e2/20261022-r1';r=b/'device-checkpoint'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=json.loads((r/'expected-source-sha256.json').read_text())
for name,d in sources.items():
 assert sha(r/name)==d,name+' archived source mismatch'
 assert sha(root/name)==d,name+' workspace source changed'
binaries=json.loads((r/'binary-sha256.json').read_text())
for name,d in binaries.items():assert sha(r/name)==d,name+' binary mismatch'
assert (r/'build/e2_runner').read_bytes().startswith(b'\x7fELF')
assert (r/'build/lib/libe2_kernel.a').read_bytes().startswith(b'!<arch>\n')
case='main_u0_n17_p0_k1_q1_d1_r1_c1';s=r/'results/smoke'/case;i=r/'inputs'/case
meta=json.loads((s/'host.json').read_text());assert meta['iterations']==1 and meta['status']=='SYNC_OK';g=meta['guard_byte'];guard=bytes([g])*1024
cf=struct.unpack('<8I',(i/'config.bin').read_bytes());run=struct.unpack('<5I',(i/'run.bin').read_bytes());u,kp,n,np,orig,tiles,_,_=cf;q,depth,rounds,capture,stall=run
assert (u,tiles,q,depth,rounds)==(0,0,1,1,1)
def payload(name,size):
 data=(s/name).read_bytes();assert len(data)==size+2048,name+' length';assert data[:1024]==guard and data[-1024:]==guard,name+' guards';return data[1024:-1024]
out=payload('output-0.bin',16*np*4);assert out==bytes(16*np*4),'U0 output must be exact +0'
assert payload('snapshot-0.bin',512)==bytes([0xab])*512,'U0 snapshot touched'
assert payload('trace-0.bin',384)==bytes([0xcd])*384,'U0 trace touched'
done=struct.unpack('<96I',payload('done-0.bin',384))
for role in range(3):
 assert done[role*32:role*32+8]==(1,0,0,0,0,role,q,depth),'U0 role completion'
 assert done[role*32+8:(role+1)*32]==(0xcdcdcdcd,)*24,'U0 completion padding'
for name in ['desc','payload','cols','config','b','run']:
 raw=(i/(name+'.bin')).read_bytes();assert payload(name+'-after.bin',len(raw))==raw,name+' input changed'
assert sorted(p.name for p in s.glob('output-*.bin'))==['output-0.bin']
assert (r/'bootstrap.rc').read_text().strip()=='BOOTSTRAP_RC=1'
log=(r/'smoke.log').read_text();assert log.count('CALL_OK')==1 and '507015' in log and 'MPU address access is invalid' in log
failed=r/'results/smoke/main_u16_n17_p0_k1_q1_d1_r1_c1';assert not (failed/'host.json').exists(),'Failed U16 cannot have successful host metadata'
headers=r/'sdk-headers/kernel_operator_data_copy_impl.h';hdr=headers.read_text();assert 'copy_ubuf_to_gm' in hdr and 'ScmDataCopyND2NZMsg' in hdr and 'GetKfcClient()->AllocUB' in hdr
record={'status':'VERIFIED_PRESERVED_FAILURE','archived_sources_verified':len(sources),'workspace_source_matches':True,'actual_binaries_verified':list(binaries),'U0_independent_replay':'PASS exact zero output, no snapshot/trace writes, 3 roles completion/padding, 10 output/input guards and inputs unchanged','successful_case_calls':1,'first_nonempty_case':'U16 N17 Bitmap16 q1 depth1; failed stream sync acl507015 MPU invalid','failure_log_preserved':True,'bootstrap_returncode':1,'SDK_header_preserved':str(headers.relative_to(r)),'SDK_header_sha256':sha(headers),'E2_pass':False,'formal_batch_started':False,'E3_started':False}
(b/'local-checkpoint-audit.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False,indent=2))
