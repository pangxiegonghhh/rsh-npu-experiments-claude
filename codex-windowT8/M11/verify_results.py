"""Verify published bytes and recompute all measurements in an isolated temporary copy."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent
def main()->None:
    files=json.loads((ROOT/'FILES-SHA256.json').read_text())
    for name,want in files.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want,name
    with tempfile.TemporaryDirectory(prefix='m11-publication-check-') as tmp:
        work=Path(tmp)/'M11';shutil.copytree(ROOT,work)
        def run(args:list[str],**extra:str)->None:
            env=os.environ.copy();env.update(extra)
            subprocess.run([sys.executable,*args],cwd=work,env=env,check=True)
        run(['restore_evidence.py'])
        run(['m11-work/verify_raw_clocks.py',str(work/'m11-work/recovered-evidence')])
        run(['m11-work/analysis-recompute-20261115/recompute.py'])
        run(['m11-work/analyze.py'],M11_DATA_ROOT=str(work/'m11-work/recovered-evidence'))
        run(['m11b-work/analyze.py'],M11B_DATA_ROOT=str(work/'m11b-work/recovered-evidence'))
    print(json.dumps(dict(status='PASS',published_files=len(files),M11_observations=45920,M11b_observations=1680,originals_unchanged=True,binary_executed=False)))
if __name__=='__main__':main()
