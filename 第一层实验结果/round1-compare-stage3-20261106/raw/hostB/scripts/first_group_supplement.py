import hashlib,json
from pathlib import Path
import numpy as np
from native import BASE
from group_metadata import complete_stats
from collect_t23_first import MATRICES,dumpcsv
def rows():
 meta={r['matrix']:r for r in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};result=[]
 for m in MATRICES:
  nonempty=int(np.count_nonzero(np.load(BASE/'work/matrices'/m/'degrees.npy',mmap_mode='r')))
  for member in ['C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I','C5','C5-U','C8-METIS','C10-BP']:
   if member=='C10-BP':p=BASE/'logs/reused-orders.json';extra={}
   else:
    p=BASE/'work'/('generated' if member in ['C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I'] else 'external')/f'{m}__{member}__W16__seed0.record.json';record=json.loads(p.read_text());assert record['status']=='OK';extra=record.get('diagnostics',{})
   result.append(dict(matrix=m,member=member,W=16,seed=0,**complete_stats(member,extra,meta[m]['n'],nonempty,16,frozen_T21=member=='C10-BP'),source_record=str(p),source_record_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),metadata_supplement_only=True,order_or_UT_recomputed=False))
 assert len(result)==70;return result
if __name__=='__main__':
 out=BASE/'work/stage3-collected';out.mkdir(exist_ok=True);data=rows();dumpcsv(out/'first-delivery-group-diagnostics.csv',data);print('FIRST_GROUP_DIAGNOSTICS_SUPPLEMENT',len(data))
