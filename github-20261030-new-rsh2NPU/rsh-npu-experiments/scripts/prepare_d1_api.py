"""Supplementary D1 host API breakdown; separate binary, formal data untouched."""
from pathlib import Path
import json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import sha,read,save
D=ROOT/'results/d1'
def generate():
    src=ROOT/'diagnostics/d1/profile_runner.cpp';assert sha(src)==read(D/'build.json')['event_source_sha256'];s=src.read_text()
    s=s.replace('std::vector<std::vector<double>> eventSamples;','std::vector<std::vector<double>> eventSamples,apiSamples; double lastApi[10]{};')
    a=s.index(' void call(');b=s.index(' void collectEvents',a);call=s[a:b]
    call=call.replace('  check(aclrtRecordEvent(events[0],stream));','  auto h=Clock::now(); auto stamp=[&](int j){auto e=Clock::now();lastApi[j]=std::chrono::duration<double,std::micro>(e-h).count();h=e;};\n  check(aclrtRecordEvent(events[0],stream));stamp(0);')
    for index,needle in [(1,'  check(aclrtMemsetAsync(out->device,out->size,0,out->size,stream));'),(2,'  check(aclrtRecordEvent(events[1],stream));'),(3,'  if(c.groups)check(aclrtMemsetAsync(packed->device,packed->size,0,packed->size,stream));'),(4,'  check(aclrtRecordEvent(events[2],stream));'),(6,'  check(aclrtRecordEvent(events[3],stream));'),(7,'  if(c.groups)rsh_launch_restore(stream,c.cores*2,packed->device,map->device,out->device,config->device);'),(8,'  check(aclrtRecordEvent(events[4],stream));'),(9,'  check(aclrtSynchronizeStream(stream));')]:
        assert call.count(needle)==1;call=call.replace(needle,needle+f'stamp({index});')
    call=call.replace('  check(aclrtRecordEvent(events[3],stream));','  stamp(5);\n  check(aclrtRecordEvent(events[3],stream));')
    s=s[:a]+call+s[b:]
    s=s.replace('  if(retain)eventSamples.push_back(v);','  if(retain){eventSamples.push_back(v);apiSamples.emplace_back(lastApi,lastApi+10);}')
    pos=s.index('  f<<"],\\\"host_trace_schema')
    s=s[:pos]+'''  f<<"],\\\"host_api_schema\\\":\\\"d1-api-v1\\\",\\\"host_api_fields_us\\\":[\\\"event0\\\",\\\"out_memset_submission\\\",\\\"event1\\\",\\\"packed_memset_submission\\\",\\\"event2\\\",\\\"main_launch_submission\\\",\\\"event3\\\",\\\"restore_launch_submission\\\",\\\"event4\\\",\\\"final_sync\\\"],\\\"host_api_us\\\":[";
  for(size_t i=0;i<cases.size();++i){if(i)f<<',';f<<'[';for(size_t t=0;t<cases[i]->apiSamples.size();++t){if(t)f<<',';f<<'[';for(int j=0;j<10;++j){if(j)f<<',';f<<cases[i]->apiSamples[t][j];}f<<']';}f<<']';}
'''+s[pos:]
    q=ROOT/'diagnostics/d1/api_runner.cpp'
    if q.exists():assert q.read_text()==s
    else:q.write_text(s)
    return q

def main():
    src=generate();b=read(D/'build.json');dest=ROOT/'build_d1';obj=dest/'api_runner.cpp.o';exe=dest/'rsh_runner_api';cmd=b['compile_command'].copy();cmd[cmd.index('-c')+1]=str(src);cmd[cmd.index('-o')+1]=str(obj)
    link=b['link_command'].copy();link=[str(obj) if a.endswith('/profile_runner.cpp.o') else a for a in link];link[link.index('-o')+1]=str(exe)
    for name,c in [('compile',cmd),('link',link)]:
        r=subprocess.run(c,cwd=ROOT/'build_v4',capture_output=True,text=True,timeout=180);(D/f'api_build_{name}.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
    for name,h in b['reused_original_objects_sha256'].items():assert sha(ROOT/name)==h
    shutil.copy2(exe,D/'device_binary/rsh_runner_api');save(D/'api_build.json',{'source_sha256':sha(src),'executable_sha256':sha(exe),'parent_source_sha256':sha(ROOT/'diagnostics/d1/profile_runner.cpp'),'compile_command':cmd,'link_command':link,'kernel_recompiled':False,'query_scope':'host Clock::now around each runtime call/launch; separate diagnostic, no formal speed claims'})
if __name__=='__main__':main()
