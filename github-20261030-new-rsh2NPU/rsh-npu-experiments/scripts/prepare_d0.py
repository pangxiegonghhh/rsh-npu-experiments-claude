"""Build D0 host tracing while reusing the exact compiled Ascend kernels."""
from __future__ import annotations
import hashlib,json,shlex,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE_SHA='508f4252df1cb3a73fa6872817622772563e82f00e01f8c8c2fd874969c7ef9d'
def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def generate()->Path:
    source=(ROOT/'npu/runner.cpp').read_text()
    assert hashlib.sha256(source.encode()).hexdigest()=='682fdee747127321d8855c2036af13af8a7baa1e90a92cde088ca5f33ab97088', 'Original host source changed'
    s=source.replace('#include <vector>','#include <vector>\n#include <ctime>\n#include <sched.h>')
    needle='int main(int argc,char**argv){'
    extra='''struct HostTrace {int iteration,position,index,b,cpu_before,cpu_after;bool warm;long long start_ns,end_ns,thread_cpu_ns;};
static long long threadCpuNs(){timespec t{};if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))throw std::runtime_error("thread CPU clock unavailable");return (long long)t.tv_sec*1000000000LL+t.tv_nsec;}
'''
    s=s.replace(needle,extra+needle)
    start=s.index('  for(int w=0;w<warm;++w)')
    end=s.index('  for(auto& p:cases)p->validate',start)
    s=s[:start]+'''  std::vector<HostTrace>trace;trace.reserve((warm+repeats)*cases.size());
  auto tracedCall=[&](int iteration,int position,size_t j,bool isWarm){
   int cpu0=sched_getcpu();auto cpuStart=threadCpuNs();auto t=Clock::now();
   cases[j]->call(stream,iteration%2);
   auto e=Clock::now();auto cpuEnd=threadCpuNs();int cpu1=sched_getcpu();
   if(!isWarm)cases[j]->samples.push_back(std::chrono::duration<double,std::micro>(e-t).count());
   trace.push_back({iteration,position,(int)j,iteration%2,cpu0,cpu1,isWarm,
    std::chrono::duration_cast<std::chrono::nanoseconds>(t.time_since_epoch()).count(),
    std::chrono::duration_cast<std::chrono::nanoseconds>(e.time_since_epoch()).count(),cpuEnd-cpuStart});
  };
  for(int w=0;w<warm;++w){std::shuffle(order.begin(),order.end(),rng);int position=0;for(auto j:order)tracedCall(w,position++,j,true);}
  for(int r=0;r<repeats;++r){std::shuffle(order.begin(),order.end(),rng);int position=0;for(auto j:order)tracedCall(r,position++,j,false);}
'''+s[end:]
    old='  f<<"]}\\n";f.close();'
    assert s.count(old)==1
    new=r'''  f<<"],\"host_trace_schema\":\"d0-host-v1\",\"host_clock\":\"steady_clock_nanoseconds\",\"thread_cpu_note\":\"CLOCK_THREAD_CPUTIME_ID brackets primary wall interval; not device execution time\",\"trace\":[";
  for(size_t q=0;q<trace.size();++q){auto&t=trace[q];if(q)f<<',';f<<"{\"warm\":"<<(t.warm?"true":"false")<<",\"iteration\":"<<t.iteration<<",\"position\":"<<t.position<<",\"record_index\":"<<t.index<<",\"b_index\":"<<t.b<<",\"start_ns\":"<<t.start_ns<<",\"end_ns\":"<<t.end_ns<<",\"thread_cpu_ns\":"<<t.thread_cpu_ns<<",\"cpu_before\":"<<t.cpu_before<<",\"cpu_after\":"<<t.cpu_after<<'}';}
  f<<"]}\n";f.close();'''
    s=s.replace(old,new)
    # All device calls, clearing, validation, input allocation and dispatch remain byte-identical source.
    for name,nextname in [(' void call(', ' void validate('),(' void validate(', '\n};')]:
        assert source[source.index(name):source.index(nextname,source.index(name))]==s[s.index(name):s.index(nextname,s.index(name))]
    target=ROOT/'diagnostics/d0/runner.cpp';target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_text()==s,'Preserve an earlier different D0 source'
    else:target.write_text(s)
    return target

def build()->None:
    src=generate();base=ROOT/'build_v4';dest=ROOT/'build_d0';result=ROOT/'results/d0';result.mkdir(parents=True,exist_ok=True)
    assert digest(base/'rsh_runner')==BASE_SHA
    dest.mkdir(exist_ok=True)
    flags={}
    for line in (base/'CMakeFiles/rsh_runner.dir/flags.make').read_text().splitlines():
        if line.startswith('CXX_') and ' = ' in line:
            k,v=line.split(' = ',1);flags[k]=shlex.split(v)
    link=shlex.split((base/'CMakeFiles/rsh_runner.dir/link.txt').read_text())
    compiler=link[0];obj=dest/'runner_d0.cpp.o';exe=dest/'rsh_runner_d0'
    compile_cmd=[compiler,*flags.get('CXX_DEFINES',[]),*flags.get('CXX_INCLUDES',[]),*flags.get('CXX_FLAGS',[]),'-I'+str(ROOT/'npu'),'-c',str(src),'-o',str(obj)]
    objects={}
    for arg in link[1:]:
        p=Path(arg) if Path(arg).is_absolute() else base/arg
        if arg.endswith(('.o','.a')) and p.is_file():objects[str(p.relative_to(ROOT))]=digest(p)
    original=[i for i,arg in enumerate(link) if arg.endswith('/runner.cpp.o')];assert len(original)==1
    link[original[0]]=str(obj);link[link.index('-o')+1]=str(exe)
    for name,cmd in [('compile',compile_cmd),('link',link)]:
        r=subprocess.run(cmd,cwd=base,capture_output=True,text=True,timeout=180)
        (result/f'build_{name}.log').write_text(r.stdout+r.stderr)
        assert r.returncode==0,(name,r.returncode,r.stderr[-2000:])
    for path,h in objects.items():assert digest(ROOT/path)==h,path
    evidence={'base_executable_sha256':BASE_SHA,'diagnostic_executable_sha256':digest(exe),'base_runner_source_sha256':digest(ROOT/'npu/runner.cpp'),'diagnostic_runner_source_sha256':digest(src),'original_objects_unchanged_sha256':objects,'reused_original_objects_sha256':{k:v for k,v in objects.items() if not k.endswith('/runner.cpp.o')},'compile_command':compile_cmd,'link_command':link,'kernel_recompiled':False,'timer':'resident_synchronized_full_call_us','instrumentation':'host clocks and in-memory order trace; no device events; write trace after timings','note':'New host executable; compare all four records within this stage, not against old absolute times.'}
    (result/'build.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence),flush=True)
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--generate-only',action='store_true');args=ap.parse_args()
    if args.generate_only:print(generate())
    else:build()
