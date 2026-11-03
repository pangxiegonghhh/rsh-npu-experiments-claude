#include <acl/acl.h>
#include "common.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
#include <ctime>
#include <sched.h>
namespace fs=std::filesystem;
using Clock=std::chrono::steady_clock;
static double elapsed(Clock::time_point t){return std::chrono::duration<double,std::micro>(Clock::now()-t).count();}
static void check(aclError e){if(e!=ACL_SUCCESS)throw std::runtime_error("ACL error "+std::to_string(e));}
extern "C" void rsh_launch(void*,int,RshConfig,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);

extern "C" void rsh_launch_cube(void*,int,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);
extern "C" void rsh_launch_vector(void*,int,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);
extern "C" void rsh_launch_mix(void*,int,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);
extern "C" void rsh_launch_restore(void*,int,void*,void*,void*,void*);

struct Buffer {
 void* device=nullptr;size_t size=0;
 explicit Buffer(size_t n):size(std::max<size_t>(n,32)){check(aclrtMalloc(&device,size,ACL_MEM_MALLOC_HUGE_FIRST));}
 ~Buffer(){if(device)aclrtFree(device);}
 Buffer(const Buffer&)=delete;
 void load(const fs::path& p,size_t bytes){
  if(fs::file_size(p)!=bytes)throw std::runtime_error("Size mismatch "+p.string());
  if(!bytes)return;
  std::vector<char>x(bytes);std::ifstream f(p,std::ios::binary);f.read(x.data(),bytes);
  if(!f)throw std::runtime_error("Read failed "+p.string());
  check(aclrtMemcpy(device,size,x.data(),bytes,ACL_MEMCPY_HOST_TO_DEVICE));
 }
};
struct Case {
 std::string name;RshConfig c{};int kind=0;
 std::unique_ptr<Buffer>ptr,col,val,gp,refs,tiles,rows,rhs[2],packed,out,map,config;
 std::vector<float>gold;std::vector<uint8_t>valid;std::vector<double>samples;
 double prepareUs=0,firstUs=0,maxError=0;
 aclrtEvent events[5]{}; std::vector<std::vector<double>> eventSamples;
 ~Case(){for(auto e:events)if(e)aclrtDestroyEvent(e);}
 Case(const fs::path& dir,int cores):name(dir.filename().string()){
  std::ifstream f(dir/"config.txt");
  if(!(f>>c.m>>c.k>>c.n>>c.stride>>c.nnz>>c.groups>>c.blocks>>c.sparseRows))throw std::runtime_error("Bad config");
  c.cores=cores;
  for(auto& e:events)check(aclrtCreateEventWithFlag(&e,ACL_EVENT_TIME_LINE));
  if(c.stride<16||c.stride>256||c.stride%16||c.m<1||c.k<1||c.groups<0||c.sparseRows<0)throw std::runtime_error("Unsupported case");
  kind=(name=="V0"||name=="V0-R")?0:((name=="V1"||name=="V2"||name=="V2-R")?1:2);
  config=std::make_unique<Buffer>(sizeof(c));check(aclrtMemcpy(config->device,config->size,&c,sizeof(c),ACL_MEMCPY_HOST_TO_DEVICE));
  auto t=Clock::now();
  auto input=[&](const char* key,size_t n){auto b=std::make_unique<Buffer>(n);b->load(dir/(std::string(key)+".bin"),n);return b;};
  ptr=input("ptr",(size_t)(c.m+1)*4);col=input("cols",(size_t)c.nnz*4);val=input("values",(size_t)c.nnz*2);
  gp=input("cube_ptr",(size_t)(c.groups+1)*8);refs=input("colref",(size_t)c.blocks*16*4);
  tiles=input("tiles",(size_t)c.blocks*256*2);map=input("rowmap",(size_t)c.groups*16*4);
  rows=input("srows",(size_t)c.sparseRows*4);rhs[0]=input("rhs",(size_t)(c.k+1)*c.stride*2);
  std::vector<uint16_t>negative((size_t)(c.k+1)*c.stride);
  std::ifstream fb(dir/"rhs.bin",std::ios::binary);fb.read((char*)negative.data(),negative.size()*2);
  for(auto& x:negative)x^=0x8000;
  rhs[1]=std::make_unique<Buffer>(negative.size()*2);check(aclrtMemcpy(rhs[1]->device,rhs[1]->size,negative.data(),negative.size()*2,ACL_MEMCPY_HOST_TO_DEVICE));
  packed=std::make_unique<Buffer>((size_t)c.groups*16*c.stride*4);out=std::make_unique<Buffer>((size_t)c.m*c.stride*4);
  prepareUs=elapsed(t);
  gold.resize((size_t)c.m*c.stride);valid.resize(c.m);
  std::ifstream fg(dir/"golden.bin",std::ios::binary);fg.read((char*)gold.data(),gold.size()*4);
  std::ifstream fv(dir/"valid.bin",std::ios::binary);fv.read((char*)valid.data(),valid.size());
  if(!fg||!fv)throw std::runtime_error("Missing golden/coverage");
 }
 void call(aclrtStream stream,int b){
  check(aclrtRecordEvent(events[0],stream));
  check(aclrtMemsetAsync(out->device,out->size,0,out->size,stream));
  check(aclrtRecordEvent(events[1],stream));
  if(c.groups)check(aclrtMemsetAsync(packed->device,packed->size,0,packed->size,stream));
  check(aclrtRecordEvent(events[2],stream));
  if(kind==0)rsh_launch_vector(stream,c.cores*2,ptr->device,col->device,val->device,gp->device,refs->device,tiles->device,rows->device,rhs[b]->device,packed->device,out->device,config->device);
  else if(kind==1)rsh_launch_cube(stream,c.cores,ptr->device,col->device,val->device,gp->device,refs->device,tiles->device,rows->device,rhs[b]->device,packed->device,out->device,config->device);
  else rsh_launch_mix(stream,c.cores,ptr->device,col->device,val->device,gp->device,refs->device,tiles->device,rows->device,rhs[b]->device,packed->device,out->device,config->device);
  check(aclrtRecordEvent(events[3],stream));
  if(c.groups)rsh_launch_restore(stream,c.cores*2,packed->device,map->device,out->device,config->device);
  check(aclrtRecordEvent(events[4],stream));
  check(aclrtSynchronizeStream(stream));
 }
 void collectEvents(bool retain){
  std::vector<double> v;
  for(int j=0;j<5;++j){float ms=0;check(aclrtEventElapsedTime(&ms,events[j<4?j:0],events[j<4?j+1:4]));v.push_back(ms*1000.0);}
  if(retain)eventSamples.push_back(v);
 }
 void validate(int b){
  std::vector<float>x(gold.size());check(aclrtMemcpy(x.data(),out->size,out->device,out->size,ACL_MEMCPY_DEVICE_TO_HOST));
  for(int r=0;r<c.m;++r)if(valid[r])for(int j=0;j<c.n;++j){
   size_t q=(size_t)r*c.stride+j;float expected=b?-gold[q]:gold[q];float error=std::abs(x[q]-expected);
   if(!std::isfinite(x[q])||error>0.01f+0.01f*std::abs(expected))
    throw std::runtime_error(name+" numerical failure row="+std::to_string(r)+" col="+std::to_string(j)+" actual="+std::to_string(x[q])+" ref="+std::to_string(expected));
   maxError=std::max(maxError,(double)error);
  }
 }
};
struct HostTrace {int iteration,position,index,b,cpu_before,cpu_after;bool warm;long long start_ns,end_ns,thread_cpu_ns;};
static long long threadCpuNs(){timespec t{};if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))throw std::runtime_error("thread CPU clock unavailable");return (long long)t.tv_sec*1000000000LL+t.tv_nsec;}
int main(int argc,char**argv){
 try{
  if(argc<8)throw std::runtime_error("Usage: rsh_runner ROOT_N CORES WARM SAMPLES SEED OUTPUT_JSON VARIANT...");
  fs::path root(argv[1]),output(argv[6]);int cores=std::stoi(argv[2]),warm=std::stoi(argv[3]),repeats=std::stoi(argv[4]);
  if(cores<1||cores>24||warm<1||repeats<1)throw std::runtime_error("Invalid protocol");
  std::mt19937 rng(std::stoul(argv[5]));
  check(aclInit(nullptr));check(aclrtSetDevice(0));aclrtStream stream;check(aclrtCreateStream(&stream));
  std::vector<std::unique_ptr<Case>>cases;
  for(int i=7;i<argc;++i)cases.push_back(std::make_unique<Case>(root/argv[i],cores));
  for(auto& p:cases){auto t=Clock::now();p->call(stream,0);p->firstUs=elapsed(t);p->validate(0);p->call(stream,1);p->validate(1);}
  std::vector<size_t>order(cases.size());std::iota(order.begin(),order.end(),0);
  std::vector<HostTrace>trace;trace.reserve((warm+repeats)*cases.size());
  auto tracedCall=[&](int iteration,int position,size_t j,bool isWarm){
   int cpu0=sched_getcpu();auto cpuStart=threadCpuNs();auto t=Clock::now();
   cases[j]->call(stream,iteration%2);
   auto e=Clock::now();auto cpuEnd=threadCpuNs();int cpu1=sched_getcpu();
   cases[j]->collectEvents(!isWarm);
   if(!isWarm)cases[j]->samples.push_back(std::chrono::duration<double,std::micro>(e-t).count());
   trace.push_back({iteration,position,(int)j,iteration%2,cpu0,cpu1,isWarm,
    std::chrono::duration_cast<std::chrono::nanoseconds>(t.time_since_epoch()).count(),
    std::chrono::duration_cast<std::chrono::nanoseconds>(e.time_since_epoch()).count(),cpuEnd-cpuStart});
  };
  for(int w=0;w<warm;++w){std::shuffle(order.begin(),order.end(),rng);int position=0;for(auto j:order)tracedCall(w,position++,j,true);}
  for(int r=0;r<repeats;++r){std::shuffle(order.begin(),order.end(),rng);int position=0;for(auto j:order)tracedCall(r,position++,j,false);}
  for(auto& p:cases)p->validate((repeats-1)%2);
  bool mixed=false,cube=false;for(auto& p:cases){mixed=mixed||p->kind==2;cube=cube||p->c.groups>0;}
  fs::create_directories(output.parent_path());std::ofstream f(output);
  f<<"{\"schema\":\"rsh910b-v1\",\"correctness\":true,\"cores_aic\":"<<(cube?cores:0)<<",\"cores_aic_budget\":"<<cores<<",\"cores_aiv\":"<<cores*2
   <<",\"warmups\":"<<warm<<",\"repeats\":"<<repeats<<",\"timer\":\"resident_synchronized_full_call_us\",\"interleaving\":\""<<(cases.size()>1?"randomized_per_call":"single_variant")<<"\",\"b_rotation\":2,\"mixed_dispatch\":\""<<(mixed?"native_mix_1_2_not_yet_profiled":"not_used")<<"\",\"records\":[";
  for(size_t i=0;i<cases.size();++i){auto&p=*cases[i];if(i)f<<',';
   f<<"{\"variant\":\""<<p.name<<"\",\"m\":"<<p.c.m<<",\"k\":"<<p.c.k<<",\"n\":"<<p.c.n
    <<",\"cube_groups\":"<<p.c.groups<<",\"k16_tiles\":"<<p.c.blocks<<",\"aiv_rows\":"<<p.c.sparseRows
    <<",\"valid_rows\":"<<std::accumulate(p.valid.begin(),p.valid.end(),0)<<",\"device_prepare_us\":"<<p.prepareUs
    <<",\"first_us\":"<<p.firstUs<<",\"max_abs_error\":"<<p.maxError<<",\"samples_us\":[";
   for(size_t s=0;s<p.samples.size();++s){if(s)f<<',';f<<p.samples[s];}f<<"]}";
  }
  f<<"],\"event_schema\":\"d1-timeline-v1\",\"event_fields_us\":[\"out_clear\",\"packed_clear\",\"main_with_B_gather\",\"restore\",\"device_span\"],\"events\":[";
  for(size_t i=0;i<cases.size();++i){if(i)f<<',';f<<'[';for(size_t t=0;t<cases[i]->eventSamples.size();++t){if(t)f<<',';f<<'[';for(int j=0;j<5;++j){if(j)f<<',';f<<cases[i]->eventSamples[t][j];}f<<']';}f<<']';}
  f<<"],\"host_trace_schema\":\"d0-host-v1\",\"host_clock\":\"steady_clock_nanoseconds\",\"thread_cpu_note\":\"CLOCK_THREAD_CPUTIME_ID brackets primary wall interval; not device execution time\",\"trace\":[";
  for(size_t q=0;q<trace.size();++q){auto&t=trace[q];if(q)f<<',';f<<"{\"warm\":"<<(t.warm?"true":"false")<<",\"iteration\":"<<t.iteration<<",\"position\":"<<t.position<<",\"record_index\":"<<t.index<<",\"b_index\":"<<t.b<<",\"start_ns\":"<<t.start_ns<<",\"end_ns\":"<<t.end_ns<<",\"thread_cpu_ns\":"<<t.thread_cpu_ns<<",\"cpu_before\":"<<t.cpu_before<<",\"cpu_after\":"<<t.cpu_after<<'}';}
  f<<"]}\n";f.close();std::cout<<"PASS "<<cases.size()<<" variants -> "<<output<<std::endl;
  cases.clear();check(aclrtDestroyStream(stream));check(aclrtResetDevice(0));check(aclFinalize());
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}return 0;
}
