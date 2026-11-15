from pathlib import Path
import json,struct
root=Path(__file__).parent
records=[]
for c in json.loads((root/'manifest.json').read_text()):
 if c['gate_only']:continue
 raw=(root/'inputs'/(c['name']+'.config.bin')).read_bytes();cfg=list(struct.unpack('<'+'I'*(len(raw)//4),raw));rowsraw=(root/'inputs'/(c['name']+'.rows.bin')).read_bytes();rows=struct.unpack('<'+'I'*(len(rowsraw)//4),rowsraw);sel=len(set(r for r in rows if r<0xffffff00));es=4 if cfg[0] else 2;n=cfg[1];pool=2*1024**3;target=1024**3 if c['cache']=='cold' else 32*1024**2
 replicas=min((target+sel*n*es-1)//(sel*n*es),(pool//(n*es)-16)//cfg[12]);unique=replicas*sel*n*es
 assert c['cache']!='cold' or unique>=4*192*1024**2,(c['name'],unique)
 records.append(dict(case=c['name'],pool_bytes=pool,actual_unique_selected_bytes=unique,replicas=replicas,cold_requirement_pass=c['cache']!='cold' or unique>=4*192*1024**2))
(root/'cpu-working-set-audit.json').write_text(json.dumps(dict(status='PASS',points=records),indent=2));print('PASS',len(records),'stage3 working sets')
