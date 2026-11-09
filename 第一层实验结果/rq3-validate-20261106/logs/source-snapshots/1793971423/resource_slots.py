import fcntl,json,os,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def acquire():
 root=BASE/'work/cpu-slots';root.mkdir(exist_ok=True);started=time.time();pid=os.getpid();registered=False
 while True:
  with (root/'queue.guard').open('a+') as guard:
   fcntl.flock(guard,fcntl.LOCK_EX);p=root/'queue.json';queue=json.loads(p.read_text()) if p.exists() else [];alive=[]
   for entry in queue:
    try:os.kill(entry['pid'],0);alive.append(entry)
    except ProcessLookupError:pass
   queue=alive
   if not registered:queue.append(dict(pid=pid,queued_at=started));queue.sort(key=lambda e:(e['queued_at'],e['pid']));registered=True
   if queue and queue[0]['pid']==pid:
    for number in [0,1]:
     f=(root/f'slot-{number}.lock').open('a+')
     try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
     except BlockingIOError:f.close();continue
     queue=queue[1:];p.write_text(json.dumps(queue));log=BASE/'logs/cpu-slot-starts';log.mkdir(exist_ok=True);(log/f'{pid}.json').write_text(json.dumps(dict(pid=pid,slot=number,command=sys.argv,queued_at=started,acquired_at=time.time(),queue_seconds=time.time()-started,discipline='FIFO'),indent=2));return f
   p.write_text(json.dumps(queue))
  time.sleep(.5)
