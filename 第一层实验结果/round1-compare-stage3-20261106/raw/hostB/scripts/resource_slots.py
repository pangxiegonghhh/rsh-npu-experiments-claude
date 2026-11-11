import fcntl,json,os,sys,time
from memory_guard import ensure_limit
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
class HeldSlot:
 def __init__(self,normal,large):self.normal=normal;self.large=large
 def close(self):self.normal.close();self.large.close()
def acquire(root=None):
 root=Path(root) if root is not None else BASE/'work/cpu-slots';root.mkdir(exist_ok=True);started=time.time();pid=os.getpid();large=None;memory_guard_path=ensure_limit()
 if any(m in ' '.join(sys.argv) for m in ['reddit','ogbn-products']):
  large=(root/'large-graph.lock').open('a+');fcntl.flock(large,fcntl.LOCK_EX)
 while True:
  with (root/'queue.guard').open('a+') as guard:
   fcntl.flock(guard,fcntl.LOCK_EX);p=root/'queue.json';queue=json.loads(p.read_text()) if p.exists() else [];now=time.time()
   # File heartbeats avoid sandbox-restricted cross-process probes.
   queue=[e for e in queue if now-e.get('last_seen',0)<120]
   mine=next((e for e in queue if e['pid']==pid),None)
   if mine is None:queue.append(dict(pid=pid,queued_at=started,last_seen=now));queue.sort(key=lambda e:(e['queued_at'],e['pid']))
   else:mine['last_seen']=now
   if queue and queue[0]['pid']==pid:
    for number in [0,1]:
     f=(root/f'slot-{number}.lock').open('a+')
     try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
     except BlockingIOError:f.close();continue
     queue=queue[1:];p.write_text(json.dumps(queue));log=BASE/'logs/cpu-slot-starts';log.mkdir(exist_ok=True);(log/f'{pid}.json').write_text(json.dumps(dict(pid=pid,slot=number,command=sys.argv,queued_at=started,acquired_at=time.time(),queue_seconds=time.time()-started,discipline='FIFO heartbeat',queue_root=str(root),large_graph_serialized=large is not None,memory_limit_bytes=8*2**30,memory_guard_path=memory_guard_path),indent=2));return HeldSlot(f,large) if large is not None else f
   p.write_text(json.dumps(queue))
  time.sleep(.5)
