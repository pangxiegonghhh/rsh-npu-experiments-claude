from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
OLD=BASE.parent/'t21-rq2-20261106-pkg9'
PARENT=OLD/'delivery/第一层实验结果/rq2-validate-20261106'
OUT=BASE/'delivery/第一层实验结果/rq2-c6align-20261106'
PROTOCOL=BASE/'repo/第一层工作区/T21补跑-C6对齐修补'
def dump(path:Path,data:object)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));temp.replace(path)
def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def assert_runtime()->None:
    expected={'scripts/campaign.py':'3362199e76a42c5029c70a7b396de4cc71132dd3b7c4cbbbc5df45f5664c9314',
      'scripts/c6.py':'c643598bb425c7967e685ff357919512f6a66b2eba7bb7cebfef000d2db92764',
      'scripts/kahypar-cut-v1.3.7.ini':'64ebd58a4f98b95bf87ae3de5341b2be00b09e122a0526ef65a799e39bb63dd8',
      'deps/kahypar.cpython-312-darwin.so':'b8f5fff175a8984baffaa04bcbc2f54726df8e5ca7a27148c927260381bd14b7'}
    for name,wanted in expected.items():assert sha(BASE/name)==wanted,name
