"""Archive final rolling documents plus the parent full-backup verification; no device work."""
from pathlib import Path
import argparse,hashlib,json,tarfile,tempfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',required=True);ap.add_argument('--date',required=True);a=ap.parse_args();assert a.stage.replace('_','').isalnum() and a.date.isdigit()
    verification=ROOT/'results'/('backup_verification_'+a.stage+'.json');v=json.loads(verification.read_text());assert v['all_hashes_passed'] and all(r['exit']==0 for r in v['isolated_audits'].values())
    names=['实验记录.md','续跑说明.md','task_plan.md','备份清单.md','恢复环境.md','scripts/backup_closeout.py',str(verification.relative_to(ROOT))]
    for filename in ['task_plan.md','shutdown.json','shutdown-state.txt','shutdown.png','session_state.json']:
        p=ROOT/'results'/a.stage/filename
        if p.exists():names.append(str(p.relative_to(ROOT)))
    manifest={'parent_archive':v['archive'],'parent_archive_sha256':v['sha256'],'files':{n:sha(ROOT/n) for n in names}}
    target=ROOT/'artifacts/backups'/f'rsh-910b-{a.stage}-closeout-{a.date}.tar.gz';assert not target.exists()
    with tempfile.TemporaryDirectory() as td:
        mf=Path(td)/'closeout_manifest.json';mf.write_text(json.dumps(manifest,indent=2)+'\n')
        with tarfile.open(target,'w:gz',dereference=True) as tar:
            for name in names:tar.add(ROOT/name,arcname=name,recursive=False)
            tar.add(mf,arcname='closeout_manifest.json')
        with tarfile.open(target) as tar:
            for name,h in manifest['files'].items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==h
    h=sha(target);target.with_name(target.name+'.sha256').write_text(h+'  '+target.name+'\n');out={'passed':True,'archive':str(target.relative_to(ROOT)),'sha256':h,'bytes':target.stat().st_size,'files':len(names),'parent_archive_sha256':v['sha256']};(ROOT/'results'/f'backup_verification_{a.stage}_closeout.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
