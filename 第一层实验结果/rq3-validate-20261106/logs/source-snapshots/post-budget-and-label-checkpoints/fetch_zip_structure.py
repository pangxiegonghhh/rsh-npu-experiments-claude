import argparse,io,json,ssl,struct,time,traceback,urllib.request,zipfile,zlib,hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
class Remote(io.RawIOBase):
 def __init__(self,url,log):
  self.url=url;self.log=log;self.ctx=ssl.create_default_context(cafile='/etc/ssl/cert.pem');self.pos=0
  req=urllib.request.Request(url,method='HEAD')
  with urllib.request.urlopen(req,context=self.ctx,timeout=30) as r:self.size=int(r.headers['Content-Length']);log.append(dict(method='HEAD',url=r.url,status=r.status,headers=dict(r.headers)))
 def seek(self,off,whence=0):self.pos=off if whence==0 else self.pos+off if whence==1 else self.size+off;return self.pos
 def tell(self):return self.pos
 def readable(self):return True
 def seekable(self):return True
 def response(self,start,end):
  req=urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}'})
  r=urllib.request.urlopen(req,context=self.ctx,timeout=60);self.log.append(dict(start=start,end=end,status=r.status,headers=dict(r.headers)))
  if r.status!=206:r.close();raise RuntimeError('official server did not honor range request')
  return r
 def read(self,size=-1):
  if size<0:size=self.size-self.pos
  if size==0:return b''
  with self.response(self.pos,min(self.size-1,self.pos+size-1)) as r:b=r.read()
  self.pos+=len(b);return b
def fetch(url,needle,out):
 requests=[];record=dict(url=url,member_needle=needle,start=time.time(),status='INCOMPLETE',requests=requests)
 try:
  remote=Remote(url,requests);z=zipfile.ZipFile(remote);record['members']=[dict(name=x.filename,size=x.file_size,compressed=x.compress_size,CRC=x.CRC,offset=x.header_offset,method=x.compress_type) for x in z.infolist()];selected=[x for x in z.infolist() if needle in x.filename]
  if len(selected)!=1:raise RuntimeError('member selector not unique: '+str([x.filename for x in selected]))
  info=selected[0];remote.seek(info.header_offset);header=remote.read(30);h=struct.unpack('<4s5H3L2H',header);start=info.header_offset+30+h[-2]+h[-1];out.parent.mkdir(parents=True,exist_ok=True);part=out.with_suffix(out.suffix+'.part');crc=0;written=0;sha=hashlib.sha256();dec=zlib.decompressobj(-15) if info.compress_type==8 else None
  if info.compress_type not in [0,8]:raise RuntimeError('unsupported compression')
  with remote.response(start,start+info.compress_size-1) as response,part.open('wb') as f:
   while True:
    chunk=response.read(2**20)
    if not chunk:break
    data=dec.decompress(chunk) if dec else chunk;f.write(data);sha.update(data);crc=zlib.crc32(data,crc);written+=len(data)
   if dec:
    data=dec.flush();f.write(data);sha.update(data);crc=zlib.crc32(data,crc);written+=len(data)
  assert crc==info.CRC and written==info.file_size,(crc,info.CRC,written,info.file_size);part.rename(out);record.update(status='OK',selected_member=info.filename,path=str(out),sha256=sha.hexdigest(),size=written,member_CRC_verified=True,archive_size=remote.size,archive_sha256=None,archive_note='official archive fetched by exact byte ranges; selected structure member fully downloaded, CRC and sha256 recorded; feature/label members not downloaded')
 except Exception as e:record.update(error=str(e),traceback=traceback.format_exc())
 record.update(end=time.time());(BASE/'logs'/('fetch-'+out.stem+'.json')).write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k not in ['requests','members','traceback']}),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('matrix');args=ap.parse_args()
 if args.matrix=='reddit':fetch('https://data.dgl.ai/dataset/reddit.zip','reddit_graph.npz',BASE/'inputs/second/reddit_graph.npz')
 else:fetch('https://snap.stanford.edu/ogb/data/nodeproppred/products.zip','raw/edge.csv.gz',BASE/'inputs/second/products-edge.csv.gz')
