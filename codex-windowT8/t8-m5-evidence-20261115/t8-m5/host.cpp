#include <acl/acl.h>
#include <vector>
#include <iostream>
#include <fstream>
#include <stdexcept>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <filesystem>
#include <algorithm>
#include <random>
#include <string>
#include <set>
extern "C" void t8_launch(void*,void*,void*,void*,void*,void*,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t);
void ck(aclError e){if(e)throw std::runtime_error("ACL="+std::to_string(e));}
struct Mem{void*raw=nullptr;size_t bytes;Mem(size_t n):bytes(n){ck(aclrtMalloc(&raw,n+2048,ACL_MEM_MALLOC_HUGE_FIRST));ck(aclrtMemset(raw,n+2048,0x5a,n+2048));}void*ptr(){return (char*)raw+1024;}~Mem(){if(raw)aclrtFree(raw);}void guards(){std::vector<uint8_t>a(1024),b(1024);ck(aclrtMemcpy(a.data(),1024,raw,1024,ACL_MEMCPY_DEVICE_TO_HOST));ck(aclrtMemcpy(b.data(),1024,(char*)raw+1024+bytes,1024,ACL_MEMCPY_DEVICE_TO_HOST));for(int k=0;k<1024;k++)if(a[k]!=0x5a||b[k]!=0x5a)throw std::runtime_error("GM guard");}};
struct Case{uint32_t dt,kind,split,s,h,gap,n;std::string name()const{return std::string(dt?"f32":"f16")+"-"+(kind?"nz":"nd")+"-"+(split?"split":"merge")+"-s"+std::to_string(s)+"-h"+std::to_string(h)+"-gap"+std::to_string(gap)+"-n"+std::to_string(n);}};
float hf(uint16_t h){return std::ldexp(1.0f+(h&1023)/1024.0f,int((h>>10)&31)-15);}
void dump(const std::filesystem::path&p,const void*d,size_t n){std::ofstream f(p,std::ios::binary);f.write((const char*)d,n);}
struct Probe{
 Case c;uint32_t es,srcRows,dataBytes,bytes;Mem in,seed,eye,out,stats;std::vector<uint16_t>x,expect;std::vector<float>y;std::vector<uint32_t>ticks;
 Probe(Case a):c(a),es(c.dt?4:2),srcRows(c.s*c.h+(c.s-1)*c.gap),dataBytes(c.kind?((c.s*c.h+15)/16)*16*c.n*es:((c.s*c.h*c.n*es+511)/512)*512),bytes(dataBytes+1024),in(size_t(srcRows)*c.n*es),seed(bytes),eye(512),out(size_t(bytes)*2),stats(128),x(in.bytes/2),expect(bytes/2,0x5a5a),y(bytes/2),ticks(32){
  for(uint32_t r=0;r<srcRows;r++)for(uint32_t j=0;j<c.n;j++){auto k=(size_t(r)*c.n+j)*(es/2);if(c.dt){x[k]=0x2000+((r*31+j*7)%8192);x[k+1]=0x3f00+(r%128);}else x[k]=0x2400+((r*31+j*7)%8192);}
  for(uint32_t s=0;s<c.s;s++)for(uint32_t r=0;r<c.h;r++)for(uint32_t j=0;j<c.n;j++)for(uint32_t part=0;part<es/2;part++){
   auto sr=s*(c.h+c.gap)+r,dr=s*c.h+r,c0=32/es,kp=((c.s*c.h+15)/16)*16;
   size_t dest=256+(c.kind?(size_t(j/c0)*kp*c0+dr*c0+j%c0)*(es/2):(size_t(dr)*c.n+j)*(es/2));expect[dest+part]=x[(size_t(sr)*c.n+j)*(es/2)+part];
  }
  ck(aclrtMemcpy(in.ptr(),in.bytes,x.data(),in.bytes,ACL_MEMCPY_HOST_TO_DEVICE));std::vector<uint16_t>id(256);for(int k=0;k<16;k++)id[k*16+k]=0x3c00;ck(aclrtMemcpy(eye.ptr(),512,id.data(),512,ACL_MEMCPY_HOST_TO_DEVICE));
 }
 uint64_t run(aclrtStream stream,uint32_t rounds){t8_launch(stream,in.ptr(),seed.ptr(),eye.ptr(),out.ptr(),stats.ptr(),c.dt,c.kind,c.split,c.s,c.h,c.gap,c.n,rounds,bytes);ck(aclrtSynchronizeStream(stream));ck(aclrtMemcpy(y.data(),out.bytes,out.ptr(),out.bytes,ACL_MEMCPY_DEVICE_TO_HOST));ck(aclrtMemcpy(ticks.data(),128,stats.ptr(),128,ACL_MEMCPY_DEVICE_TO_HOST));uint64_t a=ticks[0]|(uint64_t(ticks[1])<<32),b=ticks[2]|(uint64_t(ticks[3])<<32);if(b<=a||ticks[4]!=rounds*(c.split?c.s:1))throw std::runtime_error("timer/config");return b-a;}
 void validate(){for(size_t j=0;j<expect.size();j++)if(y[j]!=hf(expect[j]))throw std::runtime_error("L1 readback half_index="+std::to_string(j)+" got="+std::to_string(y[j])+" expected="+std::to_string(hf(expect[j])));in.guards();seed.guards();eye.guards();out.guards();stats.guards();}
 void inputCheck(){std::vector<uint16_t>a(x.size());ck(aclrtMemcpy(a.data(),in.bytes,in.ptr(),in.bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(a!=x)throw std::runtime_error("input mutation");}
};
int main(int argc,char**argv){try{if(argc<3)throw std::runtime_error("check|time|first output-dir");std::string mode=argv[1];std::filesystem::path root=argv[2];std::filesystem::create_directories(root);std::vector<Case>cases;
 for(uint32_t dt:{0u,1u})for(uint32_t kind:{0u,1u})for(uint32_t split:{0u,1u})for(uint32_t n:{16u,256u}){
  for(uint32_t h:{1u,2u,4u,8u,16u,32u,64u})cases.push_back({dt,kind,split,1,h,0,n});
  for(uint32_t s:{2u,4u,8u,16u})for(uint32_t h:{1u,2u,4u})for(uint32_t gap:{2u,8u,64u})cases.push_back({dt,kind,split,s,h,gap,n});
 }
 bool quality=mode=="qualityblock";if(quality){if(argc<5)throw std::runtime_error("quality filter missing");std::set<std::string>keep;std::ifstream f(argv[4]);std::string line;while(std::getline(f,line))keep.insert(line);cases.erase(std::remove_if(cases.begin(),cases.end(),[&](const Case&c){return !keep.count(c.name());}),cases.end());mode="timeblock";}
 if(mode=="first")cases={{0,0,0,4,2,8,16},{0,1,0,4,2,8,16},{1,0,0,4,2,8,16},{1,1,0,4,2,8,16}};
 if(mode=="sentinel")cases={{0,1,0,8,2,8,256}};
 uint32_t blockId=argc>3?std::stoul(argv[3]):0;
 if(mode=="time"||mode=="timeblock")std::shuffle(cases.begin(),cases.end(),std::mt19937(20261114+blockId));
 ck(aclInit(nullptr));ck(aclrtSetDevice(0));aclrtStream stream;ck(aclrtCreateStream(&stream));std::ofstream manifest(root/"manifest.csv");manifest<<"case,dtype,api,split,segments,rows_per_segment,gap_rows,N,source_rows,L1_bytes,status\n";std::ofstream timing(root/"timing.csv");timing<<"case,batch,sample,cycles,us,api_calls\n";size_t passed=0;
 for(const auto&c:cases){Probe p(c);auto dir=root/c.name();std::filesystem::create_directories(dir);try{
  auto ticks=p.run(stream,1);dump(dir/"output-f32.bin",p.y.data(),p.out.bytes);dump(dir/"expected-half-bits.bin",p.expect.data(),p.expect.size()*2);p.validate();p.inputCheck();
  if(mode=="time")for(uint32_t batch:{64u,256u,1024u,4096u})for(int i=0;i<21;i++){auto cycles=p.run(stream,batch);p.validate();if(i)timing<<c.name()<<","<<batch<<","<<i-1<<","<<cycles<<","<<cycles/50.0<<","<<batch*(c.split?c.s:1)<<"\n";}p.inputCheck();
  if(mode=="timeblock"){std::vector<uint32_t>batches=quality?std::vector<uint32_t>{256,1024,4096,16384}:std::vector<uint32_t>{64,256,1024,4096};std::shuffle(batches.begin(),batches.end(),std::mt19937(20261114+blockId+passed));for(auto batch:batches){auto cycles=p.run(stream,batch);p.validate();timing<<c.name()<<","<<batch<<","<<blockId<<","<<cycles<<","<<cycles/50.0<<","<<batch*(c.split?c.s:1)<<"\n";}}
  if(mode=="sentinel"){for(int j=0;j<3;j++){p.run(stream,4096);p.validate();}for(int j=0;j<10;j++){auto cycles=p.run(stream,4096);p.validate();timing<<c.name()<<",4096,"<<j<<","<<cycles<<","<<cycles/50.0<<",4096\n";}}
  manifest<<c.name()<<","<<(c.dt?"FP32":"FP16")<<","<<(c.kind?"Nd2NzParams":"DataCopyParams")<<","<<c.split<<","<<c.s<<","<<c.h<<","<<c.gap<<","<<c.n<<","<<p.srcRows<<","<<p.bytes<<",PASS\n";manifest.flush();timing.flush();std::ofstream gate(dir/"gate.json");gate<<"{\"status\":\"PASS\",\"validation\":\"entire_L1_bit_labels_padding_guards_input_exact\",\"timer\":\"GetSystemCycle\",\"first_cycles\":"<<ticks<<"}";passed++;if(passed%20==0||mode=="first")std::cout<<"PASS "<<passed<<"/"<<cases.size()<<" "<<c.name()<<std::endl;
 }catch(std::exception&e){dump(dir/"failure-output-f32.bin",p.y.data(),p.out.bytes);std::ofstream f(dir/"failure.txt");f<<e.what();std::cerr<<"FAIL "<<c.name()<<" "<<e.what()<<std::endl;throw;}}
 ck(aclrtDestroyStream(stream));ck(aclrtResetDevice(0));ck(aclFinalize());std::cout<<"ALL_PASS "<<passed<<" cases mode="<<mode<<std::endl;return 0;
 }catch(std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
