"""Bounded collection of this M11b run, without logging authentication headers."""
from pathlib import Path
import json,urllib.request,urllib.error,time,subprocess,sys
from fetch_remote import BASE,NoRedirect
ROOT=Path(__file__).resolve().parent

def main()->None:
 authorization=Path('/private/tmp/m11b-jupyter-auth.header').read_text().strip().split(': ',1)[1];opener=urllib.request.build_opener(NoRedirect);deadline=time.monotonic()+1200
 print('Waiting for complete M11b archive receipt',flush=True)
 while True:
  try:
   with opener.open(urllib.request.Request(BASE+'archive-receipt.json',headers={'Authorization':authorization}),timeout=30) as r:raw=r.read()
   receipt=json.loads(raw);assert receipt['status']=='SEALED' and receipt['archive']=='m11b-evidence-complete.tar.gz';break
  except urllib.error.HTTPError as e:
   if e.code!=404:raise
  if time.monotonic()>deadline:raise TimeoutError('M11b archive did not finish sealing in 20 minutes')
  time.sleep(15)
 (ROOT/'archive-receipt.json').write_bytes(raw);print(json.dumps(receipt),flush=True)
 subprocess.run([sys.executable,str(ROOT/'fetch_remote.py'),receipt['archive'],'--out',str(ROOT/receipt['archive']),'--sha256',receipt['sha256']],check=True)
 assert (ROOT/receipt['archive']).stat().st_size==receipt['bytes']
 print('M11b_COMPLETE_ARCHIVE_RECOVERED_AND_HASH_VERIFIED',flush=True)
if __name__=='__main__':main()
