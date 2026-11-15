import json, urllib.request, hashlib
from pathlib import Path
root=Path(__file__).parent/'upstream-sources'/'upstream-idmg'
ref='ca0abfeccf957d938ac8946a987f05aa6e9ec36c'
paths=['kernels/op_kernel/spmm_ascend_cube_aic_without_pipeline.cpp','kernels/op_host/spmm_ascend_cube.cpp','extension/custom_op.cpp','extension/packed_column_reindex.h']
records=[]
for path in paths:
    url=f'https://raw.githubusercontent.com/IDMG-Lab/Ascend-SpMM/{ref}/{path}'
    with urllib.request.urlopen(url,timeout=40) as r: data=r.read()
    name=path.replace('/','__'); (root/name).write_bytes(data)
    records.append(dict(path=path,ref=ref,sha256=hashlib.sha256(data).hexdigest()))
(root/'extra-sources.json').write_text(json.dumps(records,indent=2))
