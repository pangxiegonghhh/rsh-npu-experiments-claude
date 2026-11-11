import argparse,gc,hashlib,json,time
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from native import BASE
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def run(name):
 start=time.time();out=BASE/'work/matrices'/name;out.mkdir(exist_ok=True)
 if name=='ogbn-products':
  meta=json.loads((out/'edge-parser.json').read_text());n=meta['n'];ptr=np.fromfile(out/'indptr.raw',dtype=np.int64);idx=np.memmap(out/'indices.raw',dtype=np.int32,mode='r');source=BASE/'inputs/second/products-edge.csv.gz';url='https://snap.stanford.edu/ogb/data/nodeproppred/products.zip';source_member='products/raw/edge.csv.gz'
 else:
  source=BASE/'inputs/second/reddit_graph.npz';url='https://dgl-data.s3-accelerate.amazonaws.com/dataset/reddit.zip';source_member='reddit_graph.npz';z=np.load(source);rawrow=z['row'];rawcol=z['col'];data=z['data'];n=int(z['shape'][0]);meta=dict(n=n,stored_entries=len(rawrow),diagonal_entries=int(np.count_nonzero(rawrow==rawcol)),explicit_zero_entries=int(np.count_nonzero(data==0)));del data;keep=rawrow!=rawcol;a=sp.csr_matrix((np.ones(int(keep.sum()),np.uint8),(rawrow[keep],rawcol[keep])),shape=(n,n));a.data[:]=1;del rawrow,rawcol,keep,z;gc.collect();a=a.maximum(a.T);a.sort_indices();ptr=a.indptr.astype(np.int64);idx=a.indices.astype(np.int32);meta['nnz_A0']=a.nnz
 deg=np.diff(ptr);np.save(out/'indptr.npy',ptr);np.save(out/'indices.npy',idx);np.save(out/'degrees.npy',deg.astype(np.int32));hist=np.bincount(deg);cum=np.cumsum(hist)
 taus=[(2,'fixed'),(3,'fixed')] if np.mean(deg<=3)>=.1 else [(int(np.searchsorted(cum,np.ceil(q*n))),tag) for q,tag in [(.2,'q20'),(.4,'q40')]]
 meta.update(matrix=name,status='OK',nnz_A1=int(meta['nnz_A0']+n),source_url=url,input_path=str(source),input_mtx_sha256=None,input_sha256=sha(source),source_archive_member=source_member,structure='all stored entries, including explicit zeros; symmetric expansion, diagonal removed for A0',csr_dir=str(out),csr_sha256={k:sha(out/(k+'.npy')) for k in ['indptr','indices','degrees']},degree_mean=float(np.mean(deg)),degree_median=float(np.median(deg)),degree_max=int(np.max(deg)),taus=[dict(tau=t,tau_rule=rule,resid_count=int(np.count_nonzero(deg<=t)),resid_frac=float(np.mean(deg<=t)),resid_nnz_frac=float(deg[deg<=t].sum()/deg.sum())) for t,rule in taus],adjacency_order='sorted unique original column IDs; raw integer edge/COO input fully preserved as input archive member',prepared_sec=time.time()-start)
 if name=='ogbn-products':meta['table_discrepancy']='raw edges 61,859,140 include 128 stored diagonal entries; after symmetric expansion and diagonal removal/dedup, actual nnz_A0 is authoritative; no edits to match paper table'
 (out/'metadata.json').write_text(json.dumps(meta,indent=2));p=BASE/'logs/matrices-and-taus.json';old=json.loads(p.read_text());old=[x for x in old if x['matrix']!=name]+[meta];tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(old,indent=2));tmp.replace(p);print(json.dumps(meta),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('matrix');run(ap.parse_args().matrix)
