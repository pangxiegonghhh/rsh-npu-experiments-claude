from pathlib import Path
import csv,json,struct,hashlib
p=Path(__file__).resolve().parent
def words(path):
    b=path.read_bytes();return struct.unpack('<%dI'%(len(b)//4),b)
for order in ['B0','B1']:
    table=p/'sources'/f'{order}-segtable.csv'
    if not table.exists():table=p.parent.parent/'shared/t8-cpu-prep-20261114/prep'/f'cora-A0-W16-{order}'/'replay/segtable.csv'
    expected={}
    for r in csv.DictReader(table.open()):expected.setdefault(int(r['window']),[]).extend(range(int(r['seg_start']),int(r['seg_start'])+int(r['seg_len'])))
    actual=json.loads((p/'sources'/f'{order}-rows.json').read_text())
    assert actual==[expected[i] for i in range(170)]
manifest=json.loads((p/'manifest.json').read_text());assert len(manifest)==840
for case in manifest:
    name=case['name'];root=p/'inputs';cfg=words(root/(name+'.config.bin'));rows=words(root/(name+'.rows.bin'));off=words(root/(name+'.offsets.bin'));flat=words(root/(name+'.commands.bin'));wm=words(root/(name+'.windows.bin'))
    assert len(off)==cfg[6]+1 and off[-1]*8==len(flat)
    assert len(rows)==cfg[6]*16
    for t in range(cfg[6]):
        dst=[None]*16
        for i in range(off[t],off[t+1]):
            row,h,count,stride,k,*rest=flat[i*8:i*8+8]
            assert 0<count<=16 and 0<h<=16 and (count==1 or 0<stride*cfg[1]<=65535)
            for q in range(count):
                for j in range(h):
                    x=k+q*h+j;assert dst[x] is None;dst[x]=0xffffffff if row==0xffffffff else row+q*stride+j
        assert dst==list(rows[t*16:t*16+16])
    for wi,want in enumerate(case['rows']):
        first,nt,u,r=wm[wi*4:wi*4+4];assert len(want)==u
        assert list(rows[first*16:(first+nt)*16])==want+[0xffffffff]*(nt*16-u)
    assert case['cache']!='cold' or case['unique_input_bytes']>4*201326592
hashes=json.loads((p/'input-hashes.json').read_text())
for name,h in hashes.items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==h
result=dict(status='PASS',cases=len(manifest),input_files=len(hashes),cora_original_segtable_match=True,all_commands_reconstructed=True,all_tails_and_stride_fields_checked=True)
(p/'input-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
