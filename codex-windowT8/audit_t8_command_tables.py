"""Independent CPU audit of binary DMA tables against registered geometries/CPU segtables."""
from pathlib import Path
import csv
import hashlib
import json
import struct

base=Path(__file__).resolve().parent
tree=hashlib.sha256();files=0

def words(path,logical):
    global files
    raw=path.read_bytes();assert len(raw)%4==0
    tree.update((logical+'\0'+hashlib.sha256(raw).hexdigest()+'\n').encode())
    files+=1
    return list(struct.unpack('<'+str(len(raw)//4)+'I',raw))

def read_case(root,name,prefix):
    arrays=[]
    for kind in ('config','commands','offsets'):
        filename=f'{name}.{kind}.bin'
        arrays.append(words(root/'inputs'/filename,prefix+'/inputs/'+filename))
    cfg,flat,off=arrays;assert len(flat)%8==0
    return cfg,[flat[i:i+8] for i in range(0,len(flat),8)],off

def reconstruct(commands,first,last,n):
    result=['UNWRITTEN']*16
    for p in commands[first:last]:
        row,h,count,stride,dst,unused,zero,unused2=p
        assert 0<h<=16 and 0<count<=16 and dst+h*count<=16
        assert count==1 or stride*n<=65535
        assert unused==unused2==0 and zero in (0,1)
        for matrix in range(count):
            for k in range(h):
                index=dst+matrix*h+k;assert result[index]=='UNWRITTEN'
                result[index]=None if zero else row+matrix*stride+k
    assert 'UNWRITTEN' not in result
    return result

root=base/'t8-m4-20261114'
manifest={r['name']:r for r in json.loads((root/'m4-manifest.json').read_text())}
names=sorted((root/'cases.list').read_text().splitlines());assert len(names)==2592
for name in names:
    row=manifest[name];cfg,commands,off=read_case(root,name,'t8-m4')
    assert (cfg[1],cfg[2],cfg[3],cfg[8])==(row['n'],row['u'],row['g'],len(commands))
    assert len(off)==row['u']//16+1 and off[0]==0 and off[-1]==len(commands)
    lengths=[row['u']-row['r']+1]+[1]*(row['r']-1) if row['skew'] else [row['u']//row['r']]*row['r']
    expected=[];start=0
    for h in lengths:expected.extend(range(start,start+h));start+=h+row['gap']
    assert len(expected)==row['u'] and expected[-1]+1==row['span_rows']
    for tile in range(row['u']//16):
        assert reconstruct(commands,off[tile],off[tile+1],row['n'])==expected[tile*16:tile*16+16],name
    wanted=(1024 if row['cache']=='cold' else 32)*1024**2
    assert cfg[15]*row['u']*row['n']*row['element_bytes']==wanted
    if row['interleave']:
        assert not row['skew'] and row['gap']%lengths[0]==0
        lanes=(lengths[0]+row['gap'])//lengths[0]
        assert cfg[13]==lanes and cfg[17]==row['r']*(lengths[0]+row['gap'])
        last=cfg[15]-1;base_row=(last//lanes)*cfg[17]+(last%lanes)*lengths[0]
    else:base_row=(cfg[15]-1)*row['span_rows']
    assert (base_row+row['span_rows'])*row['n']*row['element_bytes']<=row['pool_bytes']

root=base/'t8-m4-replay-20261115'
replay_manifest={r['name']:r for r in json.loads((root/'replay-manifest.json').read_text())}
expected_by_order={}
for order in ('B0','B1'):
    folder=base/'t8-cpu-prep-20261114/prep'/f'cora-A0-W16-{order}'
    source={}
    for r in csv.DictReader((folder/'replay/segtable.csv').open()):
        source.setdefault(int(r['window']),[]).extend(range(int(r['seg_start']),int(r['seg_start'])+int(r['seg_len'])))
    expected_by_order[order]=source
names=sorted((root/'cases.list').read_text().splitlines());assert len(names)==40
for name in names:
    row=replay_manifest[name];cfg,commands,off=read_case(root,name,'t8-m4-replay')
    original=expected_by_order[row['order']]
    assert len(original)==cfg[9]==170 and sum(map(len,original.values()))==row['U']
    assert len(off)==cfg[2]+1 and off[-1]==cfg[8]==len(commands)==row['api_calls']
    tile_index=0
    for window in range(len(original)):
        columns=original[window];tiles=(len(columns)+15)//16
        for tile in range(tiles):
            assert cfg[24+tile_index*3:27+tile_index*3]==[window,tile,int(tile+1==tiles)]
            wanted=columns[tile*16:tile*16+16];wanted=wanted+[None]*(16-len(wanted))
            assert reconstruct(commands,off[tile_index],off[tile_index+1],cfg[1])==wanted,name
            tile_index+=1
    assert tile_index==cfg[2]
    assert row['copies']*row['unique_B_rows']*row['n']*(4 if row['dtype'] else 2)==row['active_useful_bytes']

result=dict(status='PASS',synthetic_cases=2592,replay_cases=40,binary_input_files=files,
            aggregate_input_sha256=tree.hexdigest(),
            reference='Synthetic requested row sequences derived independently from U/R/gap/skew; Cora row sequences read from original CPU-prep segtable.csv, not reconstructed reference rows.',
            working_set_proof='Interleaved lanes partition each R*(h+gap) row group; noninterleaved windows occupy disjoint spans. Selected useful row bytes equal fixed 32 MiB/1 GiB targets.',
            scope='CPU metadata/address proof; hardware data/guard and API-count checks remain separate.')
(base/'t8-command-table-independent-audit-20261115.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
