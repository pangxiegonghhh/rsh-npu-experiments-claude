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
namespace fs=std::filesystem;
using Clock=std::chrono::steady_clock;
static double elapsed(Clock::time_point t){return std::chrono::duration<double,std::micro>(Clock::now()-t).count();}
static void check(aclError e){if(e!=ACL_SUCCESS)throw std::runtime_error("ACL error "+std::to_string(e));}
extern "C" void rsh_launch(void*,int,RshConfig,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);

static fs::path captureRoot;
struct Buffer {
 void* base=nullptr;void* device=nullptr;size_t size=0;
 explicit Buffer(size_t n):size(std::max<size_t>(n,32)){
  check(aclrtMalloc(&base,size+2048,ACL_MEM_MALLOC_HUGE_FIRST));device=(char*)base+1024;
  std::vector<unsigned char> init(size+2048,0x5a);check(aclrtMemcpy(base,init.size(),init.data(),init.size(),ACL_MEMCPY_HOST_TO_DEVICE));
 }
 ~Buffer(){if(base)aclrtFree(base);}
 Buffer(const Buffer&)=delete;
 void load(const fs::path& p,size_t bytes){
  if(fs::file_size(p)!=bytes)throw std::runtime_error("Size mismatch "+p.string());
  if(!bytes)return;std::vector<char>x(bytes);std::ifstream f(p,std::ios::binary);f.read(x.data(),bytes);
  if(!f)throw std::runtime_error("Read failed "+p.string());
  check(aclrtMemcpy(device,size,x.data(),bytes,ACL_MEMCPY_HOST_TO_DEVICE));
 }
 void verify(const fs::path& save={}){
  std::vector<unsigned char>x(size+2048);check(aclrtMemcpy(x.data(),x.size(),base,x.size(),ACL_MEMCPY_DEVICE_TO_HOST));
  for(size_t i=0;i<1024;++i)if(x[i]!=0x5a||x[1024+size+i]!=0x5a)throw std::runtime_error("GM guard changed");
  if(!save.empty()){std::ofstream f(save,std::ios::binary);f.write((char*)x.data(),x.size());}
 }
};
struct Case {
 std::string name,caseId;std::vector<int32_t> hostmap;RshConfig c{};int kind=0;
 std::unique_ptr<Buffer>ptr,col,val,gp,refs,tiles,rows,rhs[2],packed,out,map,config;
 std::vector<float>gold;std::vector<uint8_t>valid;std::vector<double>samples;
 double prepareUs=0,firstUs=0,maxError=0;
 Case(const fs::path& dir,int cores):name(dir.filename().string()){
  std::ifstream f(dir/"config.txt");
  if(!(f>>c.m>>c.k>>c.n>>c.stride>>c.nnz>>c.groups>>c.blocks>>c.sparseRows))throw std::runtime_error("Bad config");
  c.cores=cores;caseId=dir.parent_path().filename().string()+"-"+name;hostmap.resize(c.groups*16);std::ifstream fm(dir/"rowmap.bin",std::ios::binary);fm.read((char*)hostmap.data(),hostmap.size()*4);
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
  check(aclrtMemsetAsync(out->device,out->size,0,out->size,stream));
  if(c.groups)check(aclrtMemsetAsync(packed->device,packed->size,0,packed->size,stream));
  rsh_launch(stream,kind,c,ptr->device,col->device,val->device,gp->device,refs->device,tiles->device,
             rows->device,rhs[b]->device,packed->device,out->device,map->device,config->device);
  check(aclrtSynchronizeStream(stream));
 }
 void validate(int b){
  std::vector<float>x(gold.size());check(aclrtMemcpy(x.data(),out->size,out->device,out->size,ACL_MEMCPY_DEVICE_TO_HOST));
  for(int r=0;r<c.m;++r)if(valid[r])for(int j=0;j<c.stride;++j){
   size_t q=(size_t)r*c.stride+j;float expected=b?-gold[q]:gold[q];float error=std::abs(x[q]-expected);
   if(!std::isfinite(x[q])||error>0.01f+0.01f*std::abs(expected))
    throw std::runtime_error(name+" numerical failure row="+std::to_string(r)+" col="+std::to_string(j)+" actual="+std::to_string(x[q])+" ref="+std::to_string(expected));
   maxError=std::max(maxError,(double)error);
  }
  std::vector<float> pk((size_t)c.groups*16*c.stride);check(aclrtMemcpy(pk.data(),pk.size()*4,packed->device,pk.size()*4,ACL_MEMCPY_DEVICE_TO_HOST));
  for(size_t slot=0;slot<hostmap.size();++slot)for(int col=0;col<c.stride;++col){
   int row=hostmap[slot];float expected=row<0?0:gold[(size_t)row*c.stride+col];if(b)expected=-expected;
   float actual=pk[slot*c.stride+col];if(!std::isfinite(actual)||actual!=expected)throw std::runtime_error("Packed/padding error slot="+std::to_string(slot)+" col="+std::to_string(col));
  }
  fs::create_directories(captureRoot);
  for(Buffer* buf:{ptr.get(),col.get(),val.get(),gp.get(),refs.get(),tiles.get(),rows.get(),rhs[0].get(),rhs[1].get(),map.get(),config.get()})buf->verify();
  out->verify(captureRoot/(caseId+"-out-"+std::to_string(b)+".bin"));packed->verify(captureRoot/(caseId+"-packed-"+std::to_string(b)+".bin"));

 }
};
int main(int argc,char**argv){
 try{
  if(argc<8)throw std::runtime_error("Usage: rsh_runner ROOT_N CORES WARM SAMPLES SEED OUTPUT_JSON VARIANT...");
  fs::path root(argv[1]),output(argv[6]);captureRoot=output.parent_path()/"raw";int cores=std::stoi(argv[2]),warm=std::stoi(argv[3]),repeats=std::stoi(argv[4]);
  if(cores<1||cores>24||warm<1||repeats<1)throw std::runtime_error("Invalid protocol");
  std::mt19937 rng(std::stoul(argv[5]));
  check(aclInit(nullptr));check(aclrtSetDevice(0));aclrtStream stream;check(aclrtCreateStream(&stream));
  std::vector<std::unique_ptr<Case>>cases;
  for(int i=7;i<argc;++i)cases.push_back(std::make_unique<Case>(root/argv[i],cores));
  for(auto& p:cases){auto t=Clock::now();p->call(stream,0);p->firstUs=elapsed(t);p->validate(0);p->call(stream,1);p->validate(1);}
  std::vector<size_t>order(cases.size());std::iota(order.begin(),order.end(),0);
  for(int w=0;w<warm;++w){std::shuffle(order.begin(),order.end(),rng);for(auto j:order)cases[j]->call(stream,w%2);}
  for(int r=0;r<repeats;++r){
   std::shuffle(order.begin(),order.end(),rng);
   for(auto j:order){auto t=Clock::now();cases[j]->call(stream,r%2);cases[j]->samples.push_back(elapsed(t));}
  }
  for(auto& p:cases)p->validate((repeats-1)%2);
  bool mixed=false,cube=false;for(auto& p:cases){mixed=mixed||p->kind==2;cube=cube||p->c.groups>0;}
  fs::create_directories(output.parent_path());std::ofstream f(output);
  f<<"{\"e0_guarded\":true,\"schema\":\"rsh910b-v1\",\"correctness\":true,\"cores_aic\":"<<(cube?cores:0)<<",\"cores_aic_budget\":"<<cores<<",\"cores_aiv\":"<<cores*2
   <<",\"warmups\":"<<warm<<",\"repeats\":"<<repeats<<",\"timer\":\"resident_synchronized_full_call_us\",\"interleaving\":\""<<(cases.size()>1?"randomized_per_call":"single_variant")<<"\",\"b_rotation\":2,\"mixed_dispatch\":\""<<(mixed?"native_mix_1_2_not_yet_profiled":"not_used")<<"\",\"records\":[";
  for(size_t i=0;i<cases.size();++i){auto&p=*cases[i];if(i)f<<',';
   f<<"{\"variant\":\""<<p.name<<"\",\"m\":"<<p.c.m<<",\"k\":"<<p.c.k<<",\"n\":"<<p.c.n
    <<",\"cube_groups\":"<<p.c.groups<<",\"k16_tiles\":"<<p.c.blocks<<",\"aiv_rows\":"<<p.c.sparseRows
    <<",\"valid_rows\":"<<std::accumulate(p.valid.begin(),p.valid.end(),0)<<",\"device_prepare_us\":"<<p.prepareUs
    <<",\"first_us\":"<<p.firstUs<<",\"max_abs_error\":"<<p.maxError<<",\"samples_us\":[";
   for(size_t s=0;s<p.samples.size();++s){if(s)f<<',';f<<p.samples[s];}f<<"]}";
  }
  f<<"]}\n";f.close();std::cout<<"PASS "<<cases.size()<<" variants -> "<<output<<std::endl;
  cases.clear();check(aclrtDestroyStream(stream));check(aclrtResetDevice(0));check(aclFinalize());
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}return 0;
}
