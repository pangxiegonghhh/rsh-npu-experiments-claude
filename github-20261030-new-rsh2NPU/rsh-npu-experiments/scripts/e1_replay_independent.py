"""Independent, read-only E1 verification; never writes into sealed device evidence."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

def raw(path: Path,size: int,g: int) -> bytes:
    data=path.read_bytes()
    assert len(data)==size+2048,path
    expected=bytes([g])*1024
    assert data[:1024]==data[-1024:]==expected,path
    return data[1024:-1024]

def replay(root: Path) -> dict:
    manifest=json.loads((root/"manifest.json").read_text())
    assert len(manifest)==1988 and len({x["id"] for x in manifest})==1988
    assert Counter(x["kind"] for x in manifest)==dict.fromkeys(("dense","bitmap","local_index","dense_tail"),497)
    expected_ids={f"main_u{u}_n{n}_p{p}_k{k}" for u in (0,1,15,16,17,31,32,37,48,63) for n in (1,16,17,32,33,64) for p in range(4) for k in range(4)}
    expected_ids|={f"occupancy_z{z}_k{k}" for z in range(257) for k in range(4)}
    assert {x["id"] for x in manifest}==expected_ids
    refs={}
    for item in manifest:
        case=root/"inputs"/item["id"]
        u,kp,n,npad,orig,t,ds,ps=struct.unpack("<8I",(case/"config.bin").read_bytes())
        compact=np.frombuffer((case/"original-a.bin").read_bytes(),"<f2").reshape(16,u)
        cols=np.frombuffer((case/"cols.bin").read_bytes(),"<u4")
        b=np.frombuffer((case/"b.bin").read_bytes(),"<f2").reshape(orig+1,npad)
        c=np.zeros((16,npad),np.float64)
        for r in range(16):
            for k,col in enumerate(cols):
                c[r]+=float(compact[r,k])*b[int(col)].astype(np.float64)
        a=np.zeros((16,kp),np.float16);a[:,:u]=compact
        j=np.array([int(cols[k]) if k<u else orig for k in range(kp)],"<i4")
        assert np.isfinite(c).all() and not np.any(c[:,n:])
        for file,want in item["sha256"].items():assert hashlib.sha256((case/file).read_bytes()).hexdigest()==want
        refs[item["id"]]=(a,j,c.astype("<f4"),item)
    paths=[]
    main=json.loads((root/"checks.json").read_text());repeat=json.loads((root/"repeat-checks.json").read_text());smoke=json.loads((root/"smoke-checks.json").read_text())
    assert len(main)==1988 and len(repeat)==72 and len(smoke)==9
    assert {x["case_id"] for x in main}==expected_ids
    repeated_ids={f"main_u{u}_n{n}_p1_k{k}" for u in (17,37,63) for n in (17,64) for k in range(4)}
    for proc in range(3):
        part=[x for x in repeat if x["process"]==proc]
        assert len(part)==24 and {x["case_id"] for x in part}==repeated_ids
    for rec in main: paths.append((root/"results/main"/rec["case_id"],rec,1))
    for rec in repeat: paths.append((root/f"results/repeat-{rec['process']}"/rec["case_id"],rec,10))
    for rec in smoke: paths.append((root/"results/smoke"/rec["case_id"],rec,1))
    calls=0;source_checks=0
    for dest,rec,count in paths:
        a,j,c,info=refs[rec["case_id"]];meta=json.loads((dest/"host.json").read_text());g=meta["guard_byte"]
        assert rec["status"]=="PASS" and meta["status"]=="SYNC_OK" and meta["iterations"]==count
        assert meta["input_checked_each_call"] and meta["gm_a_mod512"]==0
        for prefix in ("expanded","refs","output","decode-debug","cube-debug"):
            got=sorted(int(p.stem[len(prefix)+1:]) for p in dest.glob(prefix+"-*.bin"))
            assert got==list(range(count)),dest
        for i in range(count):
            aa=np.frombuffer(raw(dest/f"expanded-{i}.bin",a.nbytes,g),"<f2").reshape(a.shape)
            cc=np.frombuffer(raw(dest/f"output-{i}.bin",c.nbytes,g),"<f4").reshape(c.shape)
            assert np.isfinite(aa).all() and np.array_equal(aa,-a if (i//2)%2 else a),(dest,i,"A")
            assert np.isfinite(cc).all() and np.array_equal(cc,-c if (i%2+(i//2)%2)%2 else c),(dest,i,"C")
            assert raw(dest/f"refs-{i}.bin",j.nbytes,g)==j.tobytes()
            assert struct.unpack("<4I",raw(dest/f"decode-debug-{i}.bin",16,g))==(1,info["tiles"],info["nnz"],info["U"])
            assert struct.unpack("<4I",raw(dest/f"cube-debug-{i}.bin",16,g))==((info["tiles"],16,16,info["Np"]) if info["U"] else (0,0,0,0))
            calls+=1
        case=root/"inputs"/rec["case_id"]
        for name in ("desc","cols","config"):
            original=(case/f"{name}.bin").read_bytes()
            assert raw(dest/f"{name}-after.bin",len(original),g)==original
            source_checks+=1
        payload=bytearray((case/"payload.bin").read_bytes())
        if ((count-1)//2)%2:
            for off,z,kind,vk,size in struct.iter_unpack("<QHBBI",(case/"desc.bin").read_bytes()):
                start=off if kind in (0,3) else off+(32 if kind==1 else z+z%2)
                for at in range(start,off+size,2):payload[at+1]^=0x80
        b=bytearray((case/"b.bin").read_bytes())
        if (count-1)%2:
            for at in range(1,len(b),2):b[at]^=0x80
        for name,data in (("payload",payload),("b",b)):
            assert raw(dest/f"{name}-after.bin",len(data),g)==data
            source_checks+=1
        cfg=struct.pack("<12i",16,info["Kp"],info["Np"],16,info["Kp"],info["Np"],1,1,0,0,0,1)
        assert raw(dest/"cube-config-after.bin",48,g)==cfg;source_checks+=1
    assert calls==2717
    commands=json.loads((root/"commands.json").read_text())
    negative=[x for x in commands if x["label"].startswith("reject-")]
    positive=[x for x in commands if not x["label"].startswith("reject-")]
    assert len(negative)==16 and all(x["returncode"]==1 for x in negative)
    assert len(positive)==35 and all(x["returncode"]==0 for x in positive)
    logged=sum((root/"logs"/(x["label"]+".log")).read_text().count("CALL_OK ") for x in positive)
    assert logged==2708 and (root/"smoke.log").read_text().count("CALL_OK ")==9
    for file,want in json.loads((root/"expected-source-sha256.json").read_text()).items():assert hashlib.sha256((root/file).read_bytes()).hexdigest()==want,file
    binaries=json.loads((root/"binary-sha256.json").read_text())
    for file,want in binaries.items():assert hashlib.sha256((root/file).read_bytes()).hexdigest()==want,file
    assert (root/"build/e1_runner").read_bytes()[:4]==b"\x7fELF"
    hashes=json.loads((root/"file-hashes.json").read_text())
    for file,want in hashes.items():assert hashlib.sha256((root/file).read_bytes()).hexdigest()==want,file
    return {"status":"PASS","independent_original_space_references":1988,"main_cases":1988,"repeat_calls":720,"smoke_calls":9,
            "device_case_calls_replayed":calls,"output_arrays_checked":calls*5,"source_after_buffers_checked":source_checks,
            "four_kind_coverage":"497 cases each","member_hashes_verified":len(hashes),"actual_binary_artifacts_verified":len(binaries),
            "max_abs_error":0,"raw_evidence_modified":False}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);a=p.parse_args();print(json.dumps(replay(a.root),indent=2))
