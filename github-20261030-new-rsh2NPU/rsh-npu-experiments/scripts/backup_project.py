"""Create a compact, self-contained local recovery archive (CPU/files only)."""
from pathlib import Path
import argparse,hashlib,json,tarfile,tempfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);ap.add_argument('--audit',action='store_true');ap.add_argument('--versions',nargs='+',default=['v0','v1','v2']);ap.add_argument('--verification-name',default='backup_verification_v2.json');args=ap.parse_args()
    selected=[]
    for folder in ['inputs','npu','rsh','scripts','tests','docs','results','diagnostics','cases_d0']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':selected.append(p)
    # D1 transformed physical inputs; aliases rebuilt by restore_d1_runtime --layouts.
    selected.extend(p for p in (ROOT/'cases_d1').rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts)
    # Store alias metadata as regular nested files, so compact audits need no large base inputs.
    for root in (ROOT/'cases_d1').glob('*/N*'):
        for arg in ['V0','V2','V2-Z/V2','H-V','G-only/V2','ST-only/V0']:
            selected.extend(root/arg/name for name in ['metadata.json','config.txt'] if (root/arg/name).is_file())
    # D1b aliases carry exact shared metadata/flags; dereference selected symlink files below.
    d1b_manifest=ROOT/'results/d1b/case_manifest.json'
    if d1b_manifest.exists():
        selected.extend(ROOT/p for p in json.loads(d1b_manifest.read_text())['files'] if not p.endswith('.bin'))
    for scope in ['dev','eval']:
        mp=ROOT/'results/d2'/(scope+'_case_manifest.json')
        if mp.exists():selected.extend(ROOT/p for p in json.loads(mp.read_text())['files'] if not p.endswith('.bin'))
    d3_manifest=ROOT/'results/d3/case_manifest.json'
    if d3_manifest.exists():selected.extend(ROOT/p for p in json.loads(d3_manifest.read_text())['files'] if not p.endswith('.bin'))
    selected.extend(p for p in (ROOT/'cases_d3_smoke_source').rglob('*') if p.is_file())
    selected.extend(p for p in ROOT.iterdir() if p.is_file() and p.suffix in ['.md','.txt','.toml'])
    selected.extend(p for p in (ROOT/'artifacts/cpu-only-prior-skip-T0').rglob('*') if p.is_file())
    for folder in ['cases_v0','cases_v1','cases_v2','cases_hv','cases_hv_grid','cases_hc','cases_skip']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.name in ['metadata.json','config.txt']:selected.append(p)
    selected=sorted(set(selected));manifest={'schema':'rsh910b-compact-recovery-through-d3','files':{str(p.relative_to(ROOT)):digest(p) for p in selected},'cases':'Full binary cases retained locally; restore_v0_cases/restore_v1_cases/restore_v2_cases rebuild exact measured binaries on CPU. Saved V2 order.bin and H-V default/grid routing included; restore_hv_cases/restore_hv_grid_cases rebuild them. H-C uses the identical frozen default routing, restore_hc_cases rebuilds its measured inputs. H-Skip/V0-R/V2-R use the same saved R/T; restore_skip_cases rebuilds all three exact partial layouts.','d1_cases':'D0 small inputs and physical D1 transforms included; canonical large V0/V2/HV inputs rebuilt by old CPU restore scripts; D1 aliases/remaining shared binaries rebuilt by restore_d1_runtime --layouts with hash checks.','d1b_cases':'Byte-identical D1 input aliases plus native_clear.flag; restore_d1_runtime --layouts then restore_d1b_runtime --layouts, no device execution.','d2_cases':'Saved full/G/ST numeric layouts under results/d2/plans; canonical V0/V2 and D1 smoke arrays restored first, then restore_d2_runtime --layouts resolves exact file hashes without reordering, routing or device work. Measured manifests and metadata/flags included.','d3_cases':'All frozen L/F orders, route/layout arrays including V2-Z saved under results/d3; D3 mixed small sources included; canonical V0/V2 and D1 smoke bases restored first, then restore_d3_runtime --layouts resolves exact hashes without rerunning ordering/routing/device work.','credentials_included':False}
    target=ROOT/'artifacts/backups'/args.name;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FileExistsError(target)
    with tempfile.TemporaryDirectory(prefix='rsh-manifest-') as td:
        mf=Path(td)/'recovery_manifest.json';mf.write_text(json.dumps(manifest,indent=2))
        with tarfile.open(target,'w:gz',dereference=True) as tar:
            for p in selected:tar.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
            tar.add(mf,arcname='recovery_manifest.json')
    sha=digest(target);target.with_name(target.name+'.sha256').write_text(sha+'  '+target.name+'\n')
    verification={'archive':str(target.relative_to(ROOT)),'sha256':sha,'bytes':target.stat().st_size,'files':len(selected),'all_hashes_passed':False,'isolated_audits':{}}
    with tempfile.TemporaryDirectory(prefix='rsh-v2-recovery-audit-') as td:
        temp=Path(td)
        with tarfile.open(target) as tar:tar.extractall(temp,filter='data')
        for name,h in manifest['files'].items():assert digest(temp/name)==h,name
        verification['all_hashes_passed']=True
        if args.audit:
            for v in args.versions:
                r=subprocess.run([sys.executable,str(temp/f'scripts/audit_{v}.py')],cwd=temp,capture_output=True,text=True,timeout=120)
                verification['isolated_audits'][v]={'exit':r.returncode,'output':r.stdout+r.stderr}
                if r.returncode:raise RuntimeError(verification['isolated_audits'][v])
    (ROOT/'results'/args.verification_name).write_text(json.dumps(verification,indent=2));print(json.dumps(verification,ensure_ascii=False))
if __name__=='__main__':main()
