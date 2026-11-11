import argparse,json,time,traceback,hashlib,os,sys
from pathlib import Path
from native import BASE,Matrix,Candidates
sys.dont_write_bytecode=True
from resource_slots import acquire
cpu_slot=acquire()
ap=argparse.ArgumentParser();ap.add_argument('--matrix');ap.add_argument('--method');ap.add_argument('--W',type=int,default=16);ap.add_argument('--seed',type=int,default=0);args=ap.parse_args()
out=BASE/'work/generated';out.mkdir(exist_ok=True);key=f'{args.matrix}__{args.method}__W{args.W}__seed{args.seed}'
record=dict(matrix=args.matrix,method=args.method,W=args.W,seed=args.seed,start=time.time(),status='INCOMPLETE',command=sys.argv)
try:
 m=Matrix(args.matrix);g=Candidates(m);pi,st=g.order(args.method,args.W,args.seed);g.close()
 p=out/(key+'.order.json');p.write_text(json.dumps(pi,separators=(',',':'))+'\n');record.update(status='OK',path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,diagnostics=st)
except Exception as e:record.update(error=str(e),traceback=traceback.format_exc())
record.update(end=time.time());record['seconds']=record['end']-record['start'];(out/(key+'.record.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
raise SystemExit(0 if record['status']=='OK' else 1)
