#include <acl/acl.h>
#include <vector>
#include <iostream>
#include <fstream>
#include <stdexcept>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <algorithm>
#include <random>
#include <map>
#include <memory>
#include <cmath>
namespace fs=std::filesystem;
extern "C" void t8_launch(void*,void*,void*,void*,void*,void*,void*,void*,void*,uint32_t);
void ck(aclError e){if(e)throw std::runtime_error("ACL="+std::to_string(e));}
struct Mem{void*raw=nullptr;size_t bytes;Mem(size_t n):bytes(n){ck(aclrtMalloc(&raw,n+2048,ACL_MEM_MALLOC_HUGE_FIRST));ck(aclrtMemset(raw,n+2048,0x5a,n+2048));}void*ptr(){return (char*)raw+1024;}~Mem(){if(raw)aclrtFree(raw);}void put(const void*p){ck(aclrtMemcpy(ptr(),bytes,p,bytes,ACL_MEMCPY_HOST_TO_DEVICE));}void guards(){std::vector<uint8_t>a(1024),b(1024);ck(aclrtMemcpy(a.data(),1024,raw,1024,ACL_MEMCPY_DEVICE_TO_HOST));ck(aclrtMemcpy(b.data(),1024,(char*)raw+1024+bytes,1024,ACL_MEMCPY_DEVICE_TO_HOST));for(int k=0;k<1024;k++)if(a[k]!=0x5a||b[k]!=0x5a)throw std::runtime_error("GM guard bytes="+std::to_string(bytes)+" index="+std::to_string(k)+" before="+std::to_string(a[k])+" after="+std::to_string(b[k]));}};
std::vector<uint32_t>load(const fs::path&p){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f)throw std::runtime_error("missing "+p.string());auto n=f.tellg();f.seekg(0);std::vector<uint32_t>x(size_t(n)/4);f.read((char*)x.data(),n);return x;}
void dump(const fs::path&p,const void*x,size_t n){std::ofstream f(p,std::ios::binary);f.write((const char*)x,n);}
uint16_t h16(float v){uint32_t b;std::memcpy(&b,&v,4);return uint16_t((((b>>23)&255)-127+15)<<10)|uint16_t((b&0x7fffff)>>13);}
uint32_t bv(uint32_t row,uint32_t j){return 1+(uint64_t(row)*17+j*13)%251;}
struct C4{std::string name;std::vector<uint32_t>x,cmd,off;C4(std::string a):name(a),x(load(fs::path("inputs")/(a+".config.bin"))),cmd(load(fs::path("inputs")/(a+".commands.bin"))),off(load(fs::path("inputs")/(a+".offsets.bin"))){};};
struct Pool{uint32_t dt,n;Mem b,a;std::vector<uint32_t>aRef;Pool(uint32_t dtype,uint32_t features,bool check):dt(dtype),n(features),b(check?64ull*1024*1024:2ull*1024*1024*1024),a(256*(dt?4:2)),aRef(a.bytes/4){
 size_t rows=b.bytes/(n*(dt?4:2));
 if(dt){std::vector<float>v(b.bytes/4);for(size_t r=0;r<rows;r++)for(uint32_t j=0;j<n;j++)v[r*n+j]=bv(r,j);b.put(v.data());}
 else{std::vector<uint16_t>v(b.bytes/2);for(size_t r=0;r<rows;r++)for(uint32_t j=0;j<n;j++)v[r*n+j]=h16(bv(r,j));b.put(v.data());}
 uint32_t c0=dt?8:16;auto&raw=aRef;for(uint32_t m=0;m<16;m++)for(uint32_t k=0;k<16;k++){size_t index=(k/c0)*16*c0+m*c0+k%c0;float value=1+(m*3+k*5)%7;if(dt)std::memcpy((char*)raw.data()+index*4,&value,4);else{auto h=h16(value);std::memcpy((char*)raw.data()+index*2,&h,2);}}a.put(raw.data());
 }
 void audit(){
  std::vector<uint32_t>ar(aRef.size());ck(aclrtMemcpy(ar.data(),a.bytes,a.ptr(),a.bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(ar!=aRef)throw std::runtime_error("A input mutation");
  const size_t chunk=16*1024*1024;std::vector<uint32_t>raw(chunk/4);size_t es=dt?4:2;
  for(size_t offset=0;offset<b.bytes;offset+=chunk){size_t bytes=std::min(chunk,b.bytes-offset);ck(aclrtMemcpy(raw.data(),chunk,(char*)b.ptr()+offset,bytes,ACL_MEMCPY_DEVICE_TO_HOST));for(size_t j=0;j<bytes/es;j++){size_t logical=offset/es+j;auto want=bv(logical/n,logical%n);if(dt){float got;std::memcpy(&got,(char*)raw.data()+j*4,4);if(got!=float(want))throw std::runtime_error("B input mutation");}else{uint16_t got;std::memcpy(&got,(char*)raw.data()+j*2,2);if(got!=h16(want))throw std::runtime_error("B input mutation");}}}
  a.guards();b.guards();
 }
};
struct Run{C4&c;Pool&pool;uint32_t blocks,wpc,capture;std::vector<uint32_t>cfg,bases,st;std::vector<float>ref,y;Mem gcfg,gcmd,goff,gbases,out,stats;
 Run(C4&cc,Pool&pp,bool correctness,uint32_t blockCount):c(cc),pool(pp),blocks(blockCount),wpc(correctness?std::max(2u,(3*cc.x[3]+cc.x[2]/16-1)/(cc.x[2]/16)):uint32_t(((cc.x[9]?2ull*1024*1024*1024:1ull*1024*1024*1024)+uint64_t(cc.x[2])*cc.x[1]*(cc.x[0]?4:2)*blocks-1)/(uint64_t(cc.x[2])*cc.x[1]*(cc.x[0]?4:2)*blocks))),capture(correctness),cfg(c.x),bases(size_t(wpc)*blocks),st(blocks*32),ref(size_t(capture?wpc*blocks:blocks)*16*c.x[1]),y(ref.size()),gcfg(cfg.size()*4),gcmd(c.cmd.size()*4),goff(c.off.size()*4),gbases(bases.size()*4),out(ref.size()*4),stats(st.size()*4){
  cfg[5]=wpc;cfg[6]=blocks;cfg[7]=capture;for(size_t w=0;w<bases.size();w++){uint32_t index=w%cfg[15];bases[w]=cfg[12]?(index/cfg[13])*cfg[17]+(index%cfg[13])*cfg[16]:index*cfg[14];if(uint64_t(bases[w]+cfg[14])*cfg[1]*(cfg[0]?4:2)>pool.b.bytes)throw std::runtime_error("source extent");}
  gcfg.put(cfg.data());gcmd.put(c.cmd.data());goff.put(c.off.data());gbases.put(bases.data());
  for(uint32_t o=0;o<(capture?wpc*blocks:blocks);o++){uint32_t w=capture?o:(wpc-1)*blocks+o,base=bases[w];std::vector<uint32_t>cols;uint32_t row=0;for(uint32_t s=0;s<cfg[10];s++){uint32_t len=cfg[18]?(s?1:cfg[2]-cfg[10]+1):cfg[16];for(uint32_t k=0;k<len;k++)cols.push_back(base+row+k);row+=len+cfg[11];}if(cols.size()!=cfg[2])throw std::runtime_error("U mismatch");for(uint32_t m=0;m<16;m++)for(uint32_t n=0;n<cfg[1];n++){uint32_t sum=0;for(uint32_t k=0;k<cfg[2];k++)sum+=(1+(m*3+(k%16)*5)%7)*bv(cols[k],n);ref[(size_t(o)*16+m)*cfg[1]+n]=sum;}}
 }
 double execute(aclrtStream s){t8_launch(s,pool.b.ptr(),gcfg.ptr(),gcmd.ptr(),goff.ptr(),gbases.ptr(),pool.a.ptr(),out.ptr(),stats.ptr(),blocks);ck(aclrtSynchronizeStream(s));ck(aclrtMemcpy(y.data(),out.bytes,out.ptr(),out.bytes,ACL_MEMCPY_DEVICE_TO_HOST));ck(aclrtMemcpy(st.data(),stats.bytes,stats.ptr(),stats.bytes,ACL_MEMCPY_DEVICE_TO_HOST));uint64_t lo=~uint64_t(0),hi=0;for(uint32_t k=0;k<blocks;k++){uint64_t a=st[k*32]|(uint64_t(st[k*32+1])<<32),b=st[k*32+2]|(uint64_t(st[k*32+3])<<32);if(b<=a||st[k*32+4]!=wpc*cfg[8]||st[k*32+5]!=wpc*(cfg[2]/16))throw std::runtime_error("counter mismatch");lo=std::min(lo,a);hi=std::max(hi,b);}for(size_t j=0;j<y.size();j++)if(y[j]!=ref[j])throw std::runtime_error("compute mismatch element="+std::to_string(j)+" got="+std::to_string(y[j])+" expected="+std::to_string(ref[j]));pool.b.guards();pool.a.guards();gcfg.guards();gcmd.guards();goff.guards();gbases.guards();out.guards();stats.guards();return (hi-lo)/50.0;}
};
double med(std::vector<double>v){std::sort(v.begin(),v.end());return v[v.size()/2];}
int main(int argc,char**argv){try{if(argc<3)throw std::runtime_error("first|check|timeblock output-dir [block-id] [list-file]");std::string mode=argv[1];fs::path root=argv[2];fs::create_directories(root);uint32_t block=argc>3?std::stoul(argv[3]):0;std::ifstream list(argc>4?argv[4]:"cases.list");std::vector<C4>all;std::string line;while(std::getline(list,line)){if(!line.empty()&&line.back()==char(13))line.pop_back();if(!line.empty())all.emplace_back(line);}if(all.empty())throw std::runtime_error("empty list");
 if(mode=="first"){all.erase(std::remove_if(all.begin(),all.end(),[](const C4&c){return c.name.find("core-u64-r16-")!=0||c.x[9]!=0||c.x[11]!=2||(c.x[1]!=16&&c.x[1]!=256);}),all.end());}
 std::map<std::pair<uint32_t,uint32_t>,std::vector<size_t>>groups;for(size_t i=0;i<all.size();i++)groups[{all[i].x[0],all[i].x[1]}].push_back(i);std::vector<std::pair<uint32_t,uint32_t>>keys;for(auto&x:groups)keys.push_back(x.first);std::mt19937 rng(20261114+block);if(mode=="timeblock")std::shuffle(keys.begin(),keys.end(),rng);
 ck(aclInit(nullptr));ck(aclrtSetDevice(0));ck(aclrtSetOpExecuteTimeOut(15));aclrtStream s;ck(aclrtCreateStream(&s));std::ofstream f(root/"timing.csv");f<<"case,block,windows_per_core,blocks,useful_bytes,api_calls,us,us_per_window\n";size_t done=0;
 std::ofstream registration(root/"group-registration.csv");registration<<"dtype,N,block,before_us,after_us,drift,valid,input_immutable\n";
 for(auto key:keys){
  Pool pool(key.first,key.second,mode!="timeblock");auto indices=groups[key];std::unique_ptr<Run>sentinel;double before=0,after=0;
  if(mode=="timeblock"){
   auto found=std::find_if(indices.begin(),indices.end(),[&](size_t i){auto&c=all[i];return c.x[2]==64&&c.x[10]==16&&c.x[11]==2&&c.x[3]==2&&c.x[4]==0&&c.x[9]==1&&c.name.find("-split-g2")!=std::string::npos;});
   if(found==indices.end())throw std::runtime_error("sentinel missing from group");sentinel=std::make_unique<Run>(all[*found],pool,false,24);sentinel->execute(s);std::vector<double>v;for(int j=0;j<5;j++)v.push_back(sentinel->execute(s));before=med(v);std::shuffle(indices.begin(),indices.end(),rng);
  }
  for(auto index:indices){auto&c=all[index];fs::path dir=root/c.name;fs::create_directories(dir);try{
   Run r(c,pool,mode!="timeblock",mode=="first"?1:24);r.execute(s);double us=r.execute(s);uint64_t windows=uint64_t(r.wpc)*r.blocks,bytes=windows*c.x[2]*c.x[1]*(c.x[0]?4:2),calls=windows*c.x[8];
   for(auto pair:{std::make_pair(&r.gcfg,&r.cfg),std::make_pair(&r.gcmd,&c.cmd),std::make_pair(&r.goff,&c.off),std::make_pair(&r.gbases,&r.bases)}){std::vector<uint32_t>got(pair.second->size());ck(aclrtMemcpy(got.data(),pair.first->bytes,pair.first->ptr(),pair.first->bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(got!=*pair.second)throw std::runtime_error("metadata input mutation");}
   f<<c.name<<","<<block<<","<<r.wpc<<","<<r.blocks<<","<<bytes<<","<<calls<<","<<us<<","<<us/windows<<"\n";f.flush();dump(dir/"stats.bin",r.st.data(),r.stats.bytes);if(mode!="timeblock"){dump(dir/"output-f32.bin",r.y.data(),r.out.bytes);dump(dir/"reference-f32.bin",r.ref.data(),r.out.bytes);}
   std::ofstream gate(dir/"gate.json");gate<<"{\"status\":\"PASS\",\"capture_all_windows\":"<<(r.capture?"true":"false")<<",\"last_window_per_core_verified\":true,\"api_call_count_verified\":true,\"metadata_input_immutable\":true,\"guards\":true}";done++;if(done%20==0||mode=="first")std::cout<<"PASS "<<done<<"/"<<all.size()<<" "<<c.name<<std::endl;
  }catch(std::exception&e){std::ofstream err(dir/"failure.txt");err<<e.what();std::cerr<<"FAIL "<<c.name<<" "<<e.what()<<std::endl;throw;}}
  if(sentinel){std::vector<double>v;for(int j=0;j<5;j++)v.push_back(sentinel->execute(s));after=med(v);}
  pool.audit();double drift=sentinel?std::abs(after-before)/before:0;registration<<key.first<<","<<key.second<<","<<block<<","<<before<<","<<after<<","<<drift<<","<<(drift<=.05?1:0)<<",1\n";registration.flush();std::cout<<"GROUP_COMPLETE dtype="<<key.first<<" N="<<key.second<<" drift="<<drift<<" valid="<<(drift<=.05)<<std::endl;
 }
 ck(aclrtDestroyStream(s));ck(aclrtResetDevice(0));ck(aclFinalize());std::cout<<"M4_ALL_PASS "<<done<<" mode="<<mode<<std::endl;return 0;}catch(std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
