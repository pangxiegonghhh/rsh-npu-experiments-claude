"""Prepare an evidence-bound controller record after the 2026-11-09 reboot.

This does not run a scientific job, change a raw post record, or invent an
exit code. The C8 case-level status is the existing generation status; the
actual evaluation and post outcomes remain independently INCOMPLETE.
"""
import argparse, hashlib, json, pathlib, shutil, time
BASE=pathlib.Path(__file__).resolve().parents[1]
KEY='stage3-reddit__C8-METIS__W16__seed0'
C3='stage3-reddit__C3-A__W16__seed0'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 recovery=read(BASE/'logs/reboot-recovery-20261109T0952Z/snapshot.json')
 assert recovery['completed_sweeps']==0 and not recovery['terminal_record_exists']
 assert recovery['interrupted_case']==KEY+'__tau153'
 a=read(BASE/'handoff/T23-split-20261109/assignment.json')
 assert KEY in {x['case_id'] for x in a['local_cases']}
 catalog=BASE/'work/stage3-post-catalog'/(KEY+'__tau153.json');r=read(catalog)
 assert r['case_id']==KEY and r['status']=='OK' and r['tau']==153
 eval_status=read(BASE/'work/stage3-evaluations'/KEY/'status.json')
 diag_status=read(BASE/'work/stage3-diagnostics'/KEY/'status.json')
 assert eval_status['status']=='INCOMPLETE' and eval_status['rows']==20 and diag_status['status']=='OK'
 post=[];evidence={}
 for tau in (53,153):
  k=KEY+'__tau'+str(tau);cmd=BASE/'logs'/('stage3-post-'+k+'.command.json');c=read(cmd)
  out=BASE/'work/post-e'/k/'record.json';assert not out.exists()
  if tau==53:
   assert c['status']=='INCOMPLETE' and c['exitcode']==124
   cp=BASE/'work/post-e'/k/'last-completed-sweep.checkpoint.json'
   assert sha(cp)=='1628fe227011dab80dfb59ad5e0d766d29e89072cd04ad96ba46d5d7542580b7'
  else:
   assert c['status']=='RUNNING' and c.get('exitcode') is None
   assert not (out.parent/'last-completed-sweep.checkpoint.json').exists()
  evidence[str(tau)]={'command_path':str(cmd),'command_sha256':sha(cmd),'actual_command_status':c['status'],'exitcode':c.get('exitcode')}
  post.append(str(out))
 c3cmd=BASE/'logs'/('stage3-eval-'+C3+'.command.json');c=read(c3cmd)
 assert c['status']=='RUNNING' and c.get('exitcode') is None
 assert not (BASE/'work/stage3-evaluations'/C3).exists()
 for f in (BASE/'logs/cpu-slot-starts').glob('*.json'):
  assert C3 not in f.read_text(), 'C3 evaluation had acquired a CPU slot; do not classify as unstarted'
 r.update(evaluation_status=eval_status,diagnostic_status=diag_status,post_cases=post)
 r.pop('tau',None)
 r['recovery_provenance']={'kind':'derived case-level controller record after reboot; generation status only, not whole-case PASS',
  'source_catalog':str(catalog),'source_catalog_sha256':sha(catalog),'post_attempts':evidence,
  'interruption_evidence':'logs/reboot-recovery-20261109T0952Z/snapshot.json',
  'note':'tau53 timed out; tau153 interrupted by reboot before any full checkpoint; neither raw post record exists; neither attempt is retried'}
 return r,c3cmd
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();r,c3cmd=build()
 target=BASE/'work/stage3-cases'/KEY/'record.json';assert not target.exists()
 if not args.apply:
  print(json.dumps({'plan_valid':True,'target':str(target),'post_attempts':r['recovery_provenance']['post_attempts'],'c3_queued_no_cpu':True},indent=2));return
 backup=BASE/'logs/reboot-recovery-20261109T0952Z/c3-queued-before-relaunch';backup.mkdir(exist_ok=False)
 for src in (c3cmd,c3cmd.with_suffix('').with_suffix('.stdout'),c3cmd.with_suffix('').with_suffix('.stderr')):
  assert src.exists();shutil.copyfile(src,backup/src.name);assert sha(src)==sha(backup/src.name)
 target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('x') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 receipt={'passed':True,'record_path':str(target),'record_sha256':sha(target),'raw_post_records_written':False,'science_rerun':False,'queued_c3_evaluation_logs_saved':str(backup),'post_attempts':r['recovery_provenance']['post_attempts']}
 (BASE/'logs/stage3-reboot-recovery-derived-case.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
