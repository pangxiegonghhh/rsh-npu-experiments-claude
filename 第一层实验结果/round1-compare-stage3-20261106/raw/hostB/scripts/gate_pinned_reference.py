import os
from pathlib import Path
def execute(snapshot,scope):
 previous=os.environ.pop('RQ3_LAYOUT_LIB',None)
 try:exec(compile(snapshot.read_text(),str(snapshot),'exec'),scope)
 finally:
  if previous is not None:os.environ['RQ3_LAYOUT_LIB']=previous
 expected=Path(scope['BASE'])/'work/liblayouts-v4.dylib'
 assert Path(scope['Layout'].lib._name).resolve()==expected.resolve(),'reference backend must be unchanged v4'
