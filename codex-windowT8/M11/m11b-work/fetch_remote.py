"""Fetch only M11 files using the user's existing Jupyter identity; never log it."""
from pathlib import Path,PurePosixPath
import argparse,urllib.request,urllib.parse,hashlib,json
BASE='http://36.141.21.142:38080/vm-ZvhpIN6L0epAxnlW/files/t8-m11b-20261115/'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def main()->None:
 p=argparse.ArgumentParser();p.add_argument('path');p.add_argument('--out',type=Path,required=True);p.add_argument('--auth-header',type=Path,default=Path('/private/tmp/m11b-jupyter-auth.header'));p.add_argument('--sha256');a=p.parse_args()
 n=PurePosixPath(a.path);assert not n.is_absolute() and '..' not in n.parts
 raw=a.auth_header.read_text().strip();assert raw.startswith('Authorization: token ')
 opener=urllib.request.build_opener(NoRedirect);request=urllib.request.Request(BASE+urllib.parse.quote(a.path,safe='/'),headers={'Authorization':raw.split(': ',1)[1]})
 a.out.parent.mkdir(parents=True,exist_ok=True);target=a.out.with_suffix(a.out.suffix+'.partial');h=hashlib.sha256();size=0
 with opener.open(request,timeout=120) as response, target.open('wb') as f:
  assert response.status==200
  for chunk in iter(lambda:response.read(1024*1024),b''):f.write(chunk);h.update(chunk);size+=len(chunk)
 digest=h.hexdigest()
 if a.sha256:assert digest==a.sha256,'downloaded content checksum mismatch'
 target.replace(a.out);print(json.dumps(dict(file=str(a.out),bytes=size,sha256=digest,status='PASS')))
if __name__=='__main__':main()
