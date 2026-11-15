"""Restore and verify only the published M11/M11b evidence; never execute binaries."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,shutil,tarfile
ROOT=Path(__file__).resolve().parent
def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def restore(run:str)->dict:
    folder=ROOT/run;receipt=next(r for r in json.loads((ROOT/'PUBLICATION-ARCHIVES.json').read_text()) if r['run']==run)
    archive=folder/'published-evidence.tar.gz';assert digest(archive)==receipt['published_sha256']
    manifest=json.loads((folder/'PUBLISHED-EVIDENCE-SHA256.json').read_text())['files'];dest=folder/'recovered-evidence';dest.mkdir(exist_ok=True)
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers();names=set()
        for m in members:
            name=PurePosixPath(m.name)
            assert m.isfile() and not name.is_absolute() and '..' not in name.parts and m.name not in names,m.name
            names.add(m.name)
        assert names==set(manifest)
        for m in members:
            target=dest/m.name;target.parent.mkdir(parents=True,exist_ok=True)
            assert not target.is_symlink() and all(not p.is_symlink() for p in target.parents)
            if target.exists():assert digest(target)==manifest[m.name],m.name
            else:
                with tar.extractfile(m) as source,target.open('xb') as out:shutil.copyfileobj(source,out)
            assert digest(target)==manifest[m.name],m.name
    return dict(run=run,status='PASS',published_files=len(manifest),archive_sha256=receipt['published_sha256'],binary_executed=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',choices=['m11-work','m11b-work','all'],default='all');a=p.parse_args()
    for run in (['m11-work','m11b-work'] if a.run=='all' else [a.run]):print(json.dumps(restore(run)))
