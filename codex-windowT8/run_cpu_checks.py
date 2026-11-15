"""Recompute M4/M5 statistics in scratch space, leaving evidence unchanged."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from verify_bundle import verify,ROOT
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',default='audit-output');args=parser.parse_args();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True);before=verify()
 with tempfile.TemporaryDirectory(prefix='codex-windowT8-audit-') as tmp:
  scratch=Path(tmp)
  # M4 script writes its recomputation JSON, so run it on a scratch copy.
  shutil.copyfile(ROOT/'audit_m4_recovered_statistics.py',scratch/'audit_m4_recovered_statistics.py')
  for folder in ['t8-m4-20261114','t8-m4-replay-20261115','t8-m4-recovered-statistics-20261115','t8-cpu-prep-20261114']:shutil.copytree(ROOT/folder,scratch/folder)
  shutil.copyfile(ROOT/'audit_t8_command_tables.py',scratch/'audit_t8_command_tables.py')
  tasks=[('M4-models',[sys.executable,'-X','utf8',str(scratch/'audit_m4_recovered_statistics.py')]),('command-tables',[sys.executable,'-X','utf8',str(scratch/'audit_t8_command_tables.py')]),('M5-statistics',[sys.executable,'-X','utf8',str(ROOT/'audit_m5_statistics_offline.py'),str(ROOT/'t8-m5-evidence-20261115/t8-m5')])]
  if (ROOT/'t8-m8-results-20261115').is_dir():tasks.append(('M8-statistics',[sys.executable,'-X','utf8',str(ROOT/'audit_m8_results.py'),str(ROOT/'t8-m8-results-20261115'),'--out',str(out/'M8-statistics.json')]))
  results=[]
  for name,cmd in tasks:
   log=out/(name+'.log')
   with log.open('w',encoding='utf-8') as f:r=subprocess.run(cmd,cwd=scratch,stdout=f,stderr=subprocess.STDOUT)
   results.append(dict(check=name,returncode=r.returncode,log=log.name));print(name,'PASS' if r.returncode==0 else 'FAIL',flush=True)
   if r.returncode:raise RuntimeError(name+' failed; see '+str(log))
  for file in [scratch/'t8-m4-recovered-statistics-20261115/model-recomputation-verification.json',scratch/'t8-command-table-independent-audit-20261115.json']:
   if file.exists():shutil.copyfile(file,out/file.name)
 after=verify();assert before==after
 result=dict(status='PASS',package=after,checks=results,evidence_unchanged=True);(out/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
