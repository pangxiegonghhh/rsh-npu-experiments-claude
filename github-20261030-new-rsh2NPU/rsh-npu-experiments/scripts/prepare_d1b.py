"""D1b: build only a new clear kernel, reuse exact SpMM objects; freeze byte-identical layouts."""
from __future__ import annotations
import hashlib,json,shlex,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d1b';sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import POINTS,KEYS,sha,read,save
BASES=['V0','V2','V2-Z/V2','H-V']
ARGS=['old/V0','new/V0','old/V2','new/V2','old/V2-Z/V2','new/V2-Z/V2','old/H-V','new/H-V','new/H-V']
LABELS=['Old-V0','New-V0','Old-V2','New-V2','Old-V2-Z','New-V2-Z','Old-HV','New-HV-A','New-HV-B']

def cases():
    roots=[str((ROOT/'cases_d1'/m/f'N{n}').relative_to(ROOT)) for m,n in POINTS]
    roots += [x['root'] for x in read(ROOT/'results/d1/smoke_cases.json')['cases']]
    manifest={'roots':[],'files':{},'source_roots':roots}
    for source in roots:
        src=ROOT/source;target=ROOT/'cases_d1b'/Path(source).relative_to('cases_d1');manifest['roots'].append(str(target.relative_to(ROOT)))
        for version in ['old','new']:
            for arg in BASES+(['G-only/V2','ST-only/V0'] if src.parent.name.startswith('smoke_') else []):
                parent=src/arg;dst=target/version/arg;dst.mkdir(parents=True,exist_ok=True)
                for name in ['config.txt','metadata.json']+[k+'.bin' for k in KEYS]:
                    p=dst/name
                    if p.exists():assert sha(p)==sha(parent/name)
                    else:p.symlink_to((parent/name).resolve())
                    manifest['files'][str(p.relative_to(ROOT))]=sha(p)
                if version=='new':
                    flag=dst/'native_clear.flag'
                    if flag.exists():assert flag.read_text()=='AIV_zero_v1\n'
                    else:flag.write_text('AIV_zero_v1\n')
                    manifest['files'][str(flag.relative_to(ROOT))]=sha(flag)
        for arg in BASES:
            for k in KEYS:assert sha(target/'old'/arg/(k+'.bin'))==sha(target/'new'/arg/(k+'.bin'))==sha(src/arg/(k+'.bin'))
    p=D/'case_manifest.json'
    if p.exists():assert read(p)==manifest
    else:save(p,manifest)
    return manifest

def generate(source:Path,target:Path,profile=False):
    s=source.read_text();s=s.replace('struct Buffer {','extern "C" void rsh_launch_zero(void*,int,void*,uint64_t);\nstruct Buffer {')
    s=s.replace('std::string name;RshConfig c{};int kind=0;','std::string name;RshConfig c{};int kind=0;bool nativeClear=false;')
    s=s.replace('  c.cores=cores;','  c.cores=cores;nativeClear=fs::exists(dir/"native_clear.flag");')
    old='check(aclrtMemsetAsync(out->device,out->size,0,out->size,stream));';new='if(nativeClear)rsh_launch_zero(stream,c.cores*2,out->device,out->size/4);else '+old
    assert s.count(old)==1;s=s.replace(old,new)
    old='if(c.groups)check(aclrtMemsetAsync(packed->device,packed->size,0,packed->size,stream));';new='if(c.groups){if(nativeClear)rsh_launch_zero(stream,c.cores*2,packed->device,packed->size/4);else check(aclrtMemsetAsync(packed->device,packed->size,0,packed->size,stream));}'
    assert s.count(old)==1;s=s.replace(old,new)
    # Extra validation is outside all timed calls: all unowned rows and padded columns must remain zero.
    needle='  for(int r=0;r<c.m;++r)if(valid[r])for(int j=0;j<c.n;++j){'
    s=s.replace(needle,'  for(int r=0;r<c.m;++r)for(int j=0;j<c.stride;++j)if(!valid[r]||j>=c.n){if(x[(size_t)r*c.stride+j]!=0)throw std::runtime_error(name+" unowned/padded output not zero");}\n'+needle)
    needle='<<",\\\"valid_rows\\\":"'
    assert s.count(needle)==1;s=s.replace(needle,'<<",\\\"native_clear\\\":"<<(p.nativeClear?"true":"false")'+needle)
    if target.exists():assert target.read_text()==s
    else:target.parent.mkdir(parents=True,exist_ok=True);target.write_text(s)
    return target

def sources():
    return [generate(ROOT/'diagnostics/d0/runner.cpp',ROOT/'diagnostics/d1b/runner.cpp'),generate(ROOT/'diagnostics/d1/api_runner.cpp',ROOT/'diagnostics/d1b/profile_runner.cpp',True)]

def build():
    D.mkdir(exist_ok=True);base=ROOT/'build_v4';dest=ROOT/'build_d1b';dest.mkdir(exist_ok=True)
    expected=read(ROOT/'results/d1/build.json')['reused_original_objects_sha256']
    for p,h in expected.items():assert sha(ROOT/p)==h
    for name,cmd in [('configure',['cmake','-S',str(ROOT/'diagnostics/d1b'),'-B',str(dest/'zero'),'-DASCEND_CANN_PACKAGE_PATH=/usr/local/Ascend/cann-9.0.0','-DSOC_VERSION=Ascend910B2']),('kernel',['cmake','--build',str(dest/'zero'),'-j2'])]:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=600);(D/f'build_{name}.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr[-4000:])
    libs=list((dest/'zero').rglob('librsh_zero_only.a'));assert len(libs)==1;lib=libs[0]
    flags={}
    for line in (base/'CMakeFiles/rsh_runner.dir/flags.make').read_text().splitlines():
        if line.startswith('CXX_') and ' = ' in line:k,v=line.split(' = ',1);flags[k]=shlex.split(v)
    original=shlex.split((base/'CMakeFiles/rsh_runner.dir/link.txt').read_text());executables={};commands={}
    for label,source in zip(['formal','profile','zero_probe'],sources()+[ROOT/'diagnostics/d1b/zero_probe.cpp']):
        obj=dest/(label+'.o');exe=dest/('rsh_runner_d1b_'+label);compile=[original[0],*flags.get('CXX_DEFINES',[]),*flags.get('CXX_INCLUDES',[]),*flags.get('CXX_FLAGS',[]),'-I'+str(ROOT/'npu'),'-c',str(source),'-o',str(obj)]
        link=original.copy();indices=[i for i,v in enumerate(link) if v.endswith('/runner.cpp.o')];assert len(indices)==1;link[indices[0]]=str(obj);link[link.index('-o')+1]=str(exe);link.append(str(lib))
        for phase,cmd in [('compile',compile),('link',link)]:
            p=subprocess.run(cmd,cwd=base,capture_output=True,text=True,timeout=180);(D/f'build_{label}_{phase}.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(label,phase,p.stderr[-3000:])
        commands[label]={'compile':compile,'link':link};executables[label]={'path':str(exe.relative_to(ROOT)),'sha256':sha(exe)};(D/'device_binary').mkdir(exist_ok=True);shutil.copy2(exe,D/'device_binary'/exe.name)
    for p,h in expected.items():assert sha(ROOT/p)==h
    saved=D/'build_objects';saved.mkdir(exist_ok=True);index={}
    for i,(p,h) in enumerate(expected.items()):
        q=saved/(str(i)+'_'+Path(p).name);shutil.copy2(ROOT/p,q);index[p]={'saved':str(q.relative_to(ROOT)),'sha256':h}
    q=saved/lib.name;shutil.copy2(lib,q);index[str(lib.relative_to(ROOT))]={'saved':str(q.relative_to(ROOT)),'sha256':sha(lib)}
    save(saved/'index.json',index);save(D/'build.json',{'executables':executables,'commands':commands,'new_zero_library_sha256':sha(lib),'original_spmm_objects_unchanged_sha256':expected,'spmm_kernel_recompiled':False,'new_clear_kernel_compiled':True,'clear_tile_floats':8192,'clear_cores':'2*c.cores, same AIV core budget as original clear caller; 48 formal','semantic_change':'none: full out and full packed cleared separately each call; no elimination/fusion'})
if __name__=='__main__':
    D.mkdir(exist_ok=True)
    if '--generate-only' in sys.argv:sources()
    elif '--cases-only' in sys.argv:cases()
    else:cases();build()
