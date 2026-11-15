"""Read pinned public source files; never build/install/run downloaded code."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
ITEMS=[
 ('IDMG-Lab/Ascend-SpMM','ca0abfeccf957d938ac8946a987f05aa6e9ec36c','kernels/op_kernel/spmm_ascend_cube.cpp','upstream-idmg/spmm_ascend_cube.cpp','d9561088b4553d18d464aac5c6d8b09314d93df9'),
 ('IDMG-Lab/Ascend-SpMM','ca0abfeccf957d938ac8946a987f05aa6e9ec36c','README.md','upstream-idmg/README.md','1e50ec6bf32dc47451b0a98005fbb869cc3aa033'),
 ('LfLab-AI/Ascend-NPU-SpMM','875515ab73c71bc1c72574ca97811d44eac33efb','sparse/spmm_1d/arch22/internal/spmm_1d_fp16_utils.h','upstream/spmm_1d_fp16_utils.h','5f8b8011d16932ead20346dfeeb05f2b7ff01296'),
 ('LfLab-AI/Ascend-NPU-SpMM','875515ab73c71bc1c72574ca97811d44eac33efb','sparse/spmm_1d/arch22/internal/spmm_1d_kernel_variant.inc','upstream/spmm_1d_kernel_variant.inc','068486ebb7e25c5bf376bec5c84eec804bf4bd37'),
 ('LfLab-AI/Ascend-NPU-SpMM','875515ab73c71bc1c72574ca97811d44eac33efb','sparse/spmm_1d/arch22/spmm_1d_kernel.cce','upstream/spmm_1d_kernel.cce','ddef8f7a1aa67e715290f57c4a2e03149ecd859a')]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',default='../m11-upstream');args=parser.parse_args();out=Path(args.out);records=[]
 for repo,ref,path,name,expected in ITEMS:
  url=f'https://raw.githubusercontent.com/{repo}/{ref}/{path}';request=urllib.request.Request(url,headers={'User-Agent':'codex-windowT8-source-reader'})
  with urllib.request.urlopen(request,timeout=60) as response:raw=response.read()
  actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+bytes([0])+raw).hexdigest();assert actual==expected,(path,actual,expected)
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists() and target.read_bytes()!=raw:raise RuntimeError('refuse to overwrite changed '+str(target))
  target.write_bytes(raw);records.append(dict(repo=repo,ref=ref,path=path,git_blob_sha=actual,sha256=hashlib.sha256(raw).hexdigest()));print('VERIFIED',name)
 out.mkdir(exist_ok=True);(out/'source-verification.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
if __name__=='__main__':main()
