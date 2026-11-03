"""E1 deterministic fixtures, strict device validation and archival driver."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("dense", "bitmap", "local_index", "dense_tail")
US = (0, 1, 15, 16, 17, 31, 32, 37, 48, 63)
NS = (1, 16, 17, 32, 33, 64)
DESC = struct.Struct("<QHBBI")

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p: Path, obj: object) -> None:
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

def codec():
    path = ROOT / "docs/window-format-research-20261021/format_probe.py"
    spec = importlib.util.spec_from_file_location("frozen_format", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def oracle(case: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    u,kp,n,npad,orig,t,_,_ = np.fromfile(case/"config.bin",dtype="<u4").tolist()
    compact=np.fromfile(case/"original-a.bin",dtype="<f2").reshape(16,u)
    cols=np.fromfile(case/"cols.bin",dtype="<u4")
    a=np.zeros((16,kp),dtype="<f2"); a[:,:u]=compact
    refs=np.full(kp,orig,dtype="<i4"); refs[:u]=cols
    b=np.fromfile(case/"b.bin",dtype="<f2").reshape(orig+1,npad)
    # Coordinate scatter in original column space, not the decoder/padded Cube layout.
    original=np.zeros((16,orig),np.float64)
    for k,col in enumerate(cols): original[:,int(col)]=compact[:,k].astype(np.float64)
    c=(original @ b[:orig].astype(np.float64)).astype("<f4")
    assert np.isfinite(c).all() and not np.any(c[:,n:])
    return a,refs,c

def cpu_decode(case: Path) -> np.ndarray:
    c=np.fromfile(case/"config.bin",dtype="<u4");kp=int(c[1])
    raw=(case/"payload.bin").read_bytes()
    a=np.zeros((16,kp),dtype="<f2")
    for t,(off,z,kind,vk,size) in enumerate(DESC.iter_unpack((case/"desc.bin").read_bytes())):
        stream=raw[off:off+size]
        if kind==0: tile=np.frombuffer(stream,"<f2").reshape(16,16)
        elif kind==3:
            tile=np.zeros((16,16),np.float16);tile[:,:vk]=np.frombuffer(stream,"<f2").reshape(16,vk)
        else:
            tile=np.zeros(256,np.float16)
            if kind==1:
                positions=[r*16+k for r,mask in enumerate(struct.unpack("<16H",stream[:32])) for k in range(16) if mask>>k&1]
                values=np.frombuffer(stream[32:],"<f2")
            else:
                positions=list(stream[:z]);values=np.frombuffer(stream[z+z%2:],"<f2")
            assert len(positions)==len(values)==z
            for pos,value in zip(positions,values):tile[pos]=value
            tile=tile.reshape(16,16)
        a[:,t*16:t*16+16]=tile
    return a

def prepare(out: Path) -> None:
    assert not (out/"inputs").exists(), "Never overwrite an existing fixture version"
    out.mkdir(parents=True,exist_ok=True); (out/"inputs").mkdir()
    enc=codec(); manifest=[]
    def save(name: str,u: int,n: int,compact: np.ndarray,cols: np.ndarray,group: str) -> None:
        kp=max(16,(u+15)//16*16);npad=(n+15)//16*16;t=(u+15)//16;orig=257
        dense=np.zeros((16,kp),np.float16);dense[:,:u]=compact
        tiles=dense[:,:t*16].reshape(16,t,16).transpose(1,0,2).copy()
        b=np.zeros((orig+1,npad),"<f2")
        for r in range(orig):
            for f in range(n): b[r,f]=((r*7+f*3)%31-15)/8
        for ki,kind in enumerate(KINDS):
            case=out/"inputs"/f"{name}_k{ki}";case.mkdir()
            desc,payload=enc.encode(tiles,kind,[min(16,u-j*16) for j in range(t)])
            (case/"desc.bin").write_bytes(desc);(case/"payload.bin").write_bytes(payload)
            np.asarray(cols,"<u4").tofile(case/"cols.bin");b.tofile(case/"b.bin")
            np.asarray([u,kp,n,npad,orig,t,len(desc),len(payload)],"<u4").tofile(case/"config.bin")
            np.asarray(compact,"<f2").tofile(case/"original-a.bin")
            a,refs,c=oracle(case)
            assert np.array_equal(cpu_decode(case),a),case.name
            info={"id":case.name,"group":group,"kind":kind,"U":u,"N":n,"Kp":kp,"Np":npad,"tiles":t,
                  "nnz":int(np.count_nonzero(compact)),"sha256":{p.name:sha(p) for p in case.glob("*.bin")}}
            write(case/"case.json",info);manifest.append(info)
    rng=np.random.default_rng(20261022)
    for u in US:
        for n in NS:
            for pattern,density in enumerate((.0625,.25,.75,1.)):
                cols=np.sort(rng.choice(257,u,replace=False)).astype("<u4")
                compact=rng.choice(np.array([-2,-1,-.5,.25,.5,1,2],np.float16),(16,u))
                compact[rng.random((16,u))>density]=0
                for k in range(u): compact[k%16,k]=(k%4+1)/4
                save(f"main_u{u}_n{n}_p{pattern}",u,n,compact,cols,"main")
    for z in range(257):
        a=np.zeros(256,np.float16);ids=rng.choice(256,z,replace=False)
        a[ids]=rng.choice(np.array([-2,-1,-.5,.25,.5,1,2],np.float16),z)
        save(f"occupancy_z{z}",16,16,a.reshape(16,16),np.asarray([i*13+1 for i in range(16)],"<u4"),"occupancy")
    write(out/"manifest.json",manifest)
    assert len(manifest)==1988
    # Malformed serialized fields are rejected in host-only mode before aclInit.
    invalid=out/"invalid";invalid.mkdir()
    mutations=[
        ("kind", "main_u17_n17_p1_k0", "desc.bin",10,b"\x09"),
        ("validk","main_u17_n17_p1_k0","desc.bin",27,b"\x10"),
        ("offset","main_u17_n17_p1_k0","desc.bin",0,struct.pack("<Q",2**63)),
        ("nnz","main_u17_n17_p1_k0","desc.bin",8,b"\x01\x01"),
        ("length","main_u17_n17_p1_k0","desc.bin",12,struct.pack("<I",511)),
        ("bitmap_popcount","main_u17_n17_p1_k1","payload.bin",0,bytes([((out/"inputs/main_u17_n17_p1_k1/payload.bin").read_bytes()[0])^1,(out/"inputs/main_u17_n17_p1_k1/payload.bin").read_bytes()[1]])),
        ("index_duplicate","occupancy_z256_k2","payload.bin",1,b"\x00"),
        ("column_oob","main_u17_n17_p1_k0","cols.bin",0,struct.pack("<I",257)),
        ("column_duplicate","main_u17_n17_p1_k0","cols.bin",4,(out/"inputs/main_u17_n17_p1_k0/cols.bin").read_bytes()[:4]),
        ("bad_config","main_u17_n17_p1_k0","config.bin",4,struct.pack("<I",4096)),
        ("nonfinite","occupancy_z256_k0","payload.bin",0,b"\x00\x7c"),
        ("A_tail","main_u1_n17_p1_k0","payload.bin",2,b"\x00\x3c"),
        ("bitmap_tail","main_u1_n17_p1_k1","payload.bin",0,b"\x03\x00"),
        ("index_tail","main_u1_n17_p1_k2","payload.bin",0,b"\x0f"),
        ("empty_has_desc","main_u0_n17_p1_k0","desc.bin",0,bytes(16)),
        ("B_pad","main_u17_n17_p1_k0","b.bin",(257*32)*2,b"\x00\x3c"),
    ]
    bad=[]
    for name,base,file,offset,value in mutations:
        target=invalid/name;shutil.copytree(out/"inputs"/base,target)
        p=target/file;data=bytearray(p.read_bytes());data[offset:offset+len(value)]=value;p.write_bytes(data)
        bad.append(name)
    write(out/"invalid-manifest.json",bad)
    write(out/"preflight.json",{"status":"PASS","fixtures":len(manifest),"main":960,"occupancy":1028,
          "four_kind_same_logical_inputs":True,"independent_original_column_oracles":1988,
          "note":"occupancy isolates fixed structural column domain, including zero-valued columns"})
    print("LOCAL_PREFLIGHT_PASS",len(manifest),flush=True)

def unwrap(path: Path,size: int,guard: int) -> bytes:
    x=path.read_bytes();assert len(x)==size+2048,path
    assert x[:1024]==x[-1024:]==bytes([guard])*1024,path
    return x[1024:-1024]

def validate(case: Path,dest: Path,count: int) -> dict:
    info=json.loads((case/"case.json").read_text())
    for name,want in info["sha256"].items():assert sha(case/name)==want
    a,refs,c=oracle(case);m=json.loads((dest/"host.json").read_text());g=m["guard_byte"]
    assert m["status"]=="SYNC_OK" and m["iterations"]==count and m["input_checked_each_call"]
    assert m["tiles"]==info["tiles"] and m["nnz"]==info["nnz"] and m["gm_a_mod512"]==0
    for prefix in ("expanded","refs","output","decode-debug","cube-debug"):
        assert sorted(int(p.stem.split("-")[-1]) for p in dest.glob(prefix+"-*.bin"))==list(range(count))
    maxerr=0.
    for i in range(count):
        aa=np.frombuffer(unwrap(dest/f"expanded-{i}.bin",a.nbytes,g),"<f2").reshape(a.shape)
        expected_a=-a if (i//2)%2 else a
        assert np.isfinite(aa).all() and np.array_equal(aa,expected_a),(case.name,i,"A")
        rr=np.frombuffer(unwrap(dest/f"refs-{i}.bin",refs.nbytes,g),"<i4")
        assert np.array_equal(rr,refs),(case.name,i,"refs")
        actual=np.frombuffer(unwrap(dest/f"output-{i}.bin",c.nbytes,g),"<f4").reshape(c.shape)
        want=-c if (i%2+(i//2)%2)%2 else c
        assert np.isfinite(actual).all() and np.array_equal(actual,want),(case.name,i,"C")
        maxerr=max(maxerr,float(np.max(np.abs(actual-want))))
        dz=struct.unpack("<4I",unwrap(dest/f"decode-debug-{i}.bin",16,g))
        cz=struct.unpack("<4I",unwrap(dest/f"cube-debug-{i}.bin",16,g))
        assert dz==(1,info["tiles"],info["nnz"],info["U"]),(case.name,dz)
        assert cz==((info["tiles"],16,16,info["Np"]) if info["U"] else (0,0,0,0)),(case.name,cz)
    # Input preservation, independently reconstructed final sign changes.
    payload=bytearray((case/"payload.bin").read_bytes())
    if ((count-1)//2)%2:
        for off,z,kind,vk,size in DESC.iter_unpack((case/"desc.bin").read_bytes()):
            if kind==0 or kind==3: positions=range(off,off+size,2)
            else: start=off+(32 if kind==1 else z+z%2);positions=range(start,off+size,2)
            for pos in positions:payload[pos+1]^=0x80
    b=bytearray((case/"b.bin").read_bytes())
    if (count-1)%2:
        for pos in range(1,len(b),2):b[pos]^=0x80
    for name,data in (("desc",(case/"desc.bin").read_bytes()),("payload",bytes(payload)),("cols",(case/"cols.bin").read_bytes()),("config",(case/"config.bin").read_bytes()),("b",bytes(b))):
        assert unwrap(dest/f"{name}-after.bin",len(data),g)==data,(case.name,name)
    conf=np.array([16,info["Kp"],info["Np"],16,info["Kp"],info["Np"],1,1,0,0,0,1],"<i4").tobytes()
    assert unwrap(dest/"cube-config-after.bin",len(conf),g)==conf
    return {"case_id":info["id"],"kind":info["kind"],"U":info["U"],"N":info["N"],"iterations":count,
            "status":"PASS","sequence_complete":True,"max_abs_error":maxerr}

def run(root: Path) -> None:
    infos=json.loads((root/"manifest.json").read_text());binary=root/"build/e1_runner"
    commands=[];checks=[]
    def command(argv: list[str],label: str,timeout: int=120,env: dict|None=None) -> subprocess.CompletedProcess:
        start=time.time();p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=env)
        dest=root/"logs";dest.mkdir(exist_ok=True);(dest/(label+".log")).write_bytes(p.stdout)
        commands.append({"argv":argv,"label":label,"start_unix":start,"end_unix":time.time(),"returncode":p.returncode})
        write(root/"commands.json",commands);return p
    bad=json.loads((root/"invalid-manifest.json").read_text());neg=[]
    for name in bad:
        p=command([str(binary),"--validate",str(root/"invalid"/name)],"reject-"+name)
        assert p.returncode!=0 and b"CALL_OK" not in p.stdout and b"HOST_VALIDATED" not in p.stdout,name
        neg.append({"id":name,"status":"REJECTED_BEFORE_ACL","returncode":p.returncode})
    write(root/"negative-checks.json",neg)
    # Batch in one ACL context to expose stale state across adjacent different windows.
    for batch,start in enumerate(range(0,len(infos),64)):
        chunk=infos[start:start+64];lst=root/f"batch-{batch}.txt"
        lst.write_text("".join(str(root/"inputs"/x["id"])+"\n" for x in chunk))
        p=command([str(binary),str(lst),str(root/"results/main"),"1"],f"batch-{batch}",600)
        if p.returncode:raise RuntimeError(f"Batch {batch} failed; see saved log, no silent retry")
        for x in chunk:checks.append(validate(root/"inputs"/x["id"],root/"results/main"/x["id"],1))
        write(root/"checks.json",checks);write(root/"progress.json",{"main_complete":start+len(chunk),"total":len(infos),"time":time.time()})
        print("E1_PROGRESS",start+len(chunk),len(infos),flush=True)
    repeated=[x for x in infos if x["id"].startswith("main_") and x["U"] in (17,37,63) and x["N"] in (17,64) and "_p1_" in x["id"]]
    assert len(repeated)==24
    repeatchecks=[]
    for proc in range(3):
        lst=root/f"repeat-{proc}.txt";lst.write_text("".join(str(root/"inputs"/x["id"])+"\n" for x in repeated))
        env=dict(os.environ);env["E1_GUARD_BYTE"]=str(0x36 if proc%2 else 0x5a)
        p=command([str(binary),str(lst),str(root/f"results/repeat-{proc}"),"10"],f"repeat-{proc}",600,env)
        assert p.returncode==0
        for x in repeated:
            ck=validate(root/"inputs"/x["id"],root/f"results/repeat-{proc}"/x["id"],10);ck["process"]=proc;repeatchecks.append(ck)
        write(root/"repeat-checks.json",repeatchecks)
    summary={"status":"PASS","main_cases":1988,"four_kinds":list(KINDS),"normal_window_cases":960,
             "occupancy_cases":1028,"host_rejections":len(neg),"repeat_processes":3,"repeat_configurations":24,
             "repeat_calls":720,"device_case_calls":2708,"decoder_launches":2708,
             "cube_launches":sum(x["tiles"]>0 for x in infos)+720,"max_abs_error":0,
             "all_outputs_individually_saved":True,"E2_started":False,"end_unix":time.time()}
    write(root/"summary.json",summary);print("E1_ALL_PASS",json.dumps(summary),flush=True)

def close(root: Path) -> None:
    assert (root/"driver.rc").read_text().strip()=="E1_RC=0"
    s=json.loads((root/"summary.json").read_text());assert s["status"]=="PASS"
    assert len(json.loads((root/"checks.json").read_text()))==1988
    assert sum(x["iterations"] for x in json.loads((root/"repeat-checks.json").read_text()))==720
    write(root/"closed.json",{"status":"PASS","at_unix":time.time(),"driver_rc":0,"device_case_calls":2708})
    files=sorted(p for p in root.rglob("*") if p.is_file() and p.name!="file-hashes.json" and "__pycache__" not in str(p))
    write(root/"file-hashes.json",{str(p.relative_to(root)):sha(p) for p in files})
    archive=root.parent/(root.name+"-closed.tar.gz")
    with tarfile.open(archive,"w:gz") as tf:
        for p in files+[root/"file-hashes.json"]:tf.add(p,arcname=str(p.relative_to(root)),recursive=False)
    info={"archive":archive.name,"sha256":sha(archive),"bytes":archive.stat().st_size,"members":len(files)+1,"status":"PASS"}
    write(root.parent/(root.name+"-closed-transfer.json"),info);print(json.dumps(info),flush=True)

def replay(root: Path) -> dict:
    checks=json.loads((root/"checks.json").read_text());repeated=json.loads((root/"repeat-checks.json").read_text())
    for ck in checks:validate(root/"inputs"/ck["case_id"],root/"results/main"/ck["case_id"],1)
    for ck in repeated:validate(root/"inputs"/ck["case_id"],root/f"results/repeat-{ck['process']}"/ck["case_id"],10)
    hashes=json.loads((root/"file-hashes.json").read_text())
    for file,want in hashes.items():assert sha(root/file)==want,file
    return {"status":"PASS","main_cases":len(checks),"repeat_groups":len(repeated),"device_case_calls_replayed":len(checks)+sum(x["iterations"] for x in repeated),"hashes_verified":len(hashes),"max_abs_error":0}

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("mode",choices=["prepare","run","close","replay"]);ap.add_argument("root",type=Path);args=ap.parse_args()
    result=globals()[args.mode](args.root)
    if result is not None:print(json.dumps(result,indent=2))
