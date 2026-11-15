"""Verify portable package bytes using only the Python standard library."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
def verify():
 records=json.loads((ROOT/'SHA256SUMS.json').read_text(encoding='utf-8'));fail=[]
 for name,expected in records.items():
  file=ROOT/name
  if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:fail.append(name)
 if fail:raise RuntimeError('Missing or changed package files: '+repr(fail[:20]))
 return dict(status='PASS',files=len(records),bytes=sum((ROOT/name).stat().st_size for name in records))
if __name__=='__main__':print(json.dumps(verify()))
