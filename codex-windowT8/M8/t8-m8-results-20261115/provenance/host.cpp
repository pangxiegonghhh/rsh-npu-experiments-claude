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
#include <iomanip>
namespace fs=std::filesystem;
extern "C" void t8_launch(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,uint32_t);
void ck(aclError e){if(e)throw std::runtime_error("ACL="+std::to_string(e));}
struct Mem{void*raw=nullptr;size_t bytes;Mem(size_t n):bytes(n){ck(aclrtMalloc(&raw,n+2048,ACL_MEM_MALLOC_HUGE_FIRST));ck(aclrtMemset(raw,n+2048,0x5a,n+2048));}void*ptr(){return (char*)raw+1024;}~Mem(){if(raw)aclrtFree(raw);}void put(const void*p){ck(aclrtMemcpy(ptr(),bytes,p,bytes,ACL_MEMCPY_HOST_TO_DEVICE));}void guards(){std::vector<uint8_t>a(1024),b(1024);ck(aclrtMemcpy(a.data(),1024,raw,1024,ACL_MEMCPY_DEVICE_TO_HOST));ck(aclrtMemcpy(b.data(),1024,(char*)raw+1024+bytes,1024,ACL_MEMCPY_DEVICE_TO_HOST));for(int k=0;k<1024;k++)if(a[k]!=0x5a||b[k]!=0x5a)throw std::runtime_error("GM guard bytes="+std::to_string(bytes)+" index="+std::to_string(k)+" before="+std::to_string(a[k])+" after="+std::to_string(b[k]));}};
std::vector<uint32_t>load(const fs::path&p){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f)throw std::runtime_error("missing "+p.string());auto n=f.tellg();f.seekg(0);std::vector<uint32_t>x(size_t(n)/4);f.read((char*)x.data(),n);return x;}
void dump(const fs::path&p,const void*x,size_t n){std::ofstream f(p,std::ios::binary);f.write((const char*)x,n);}
uint16_t h16(float v){if(v==0)return 0;uint32_t b;std::memcpy(&b,&v,4);return uint16_t((((b>>23)&255)-127+15)<<10)|uint16_t((b&0x7fffff)>>13);}
uint32_t bv(uint32_t row,uint32_t j){return 1+(uint64_t(row)*17+j*13)%251;}
struct C4{std::string name;std::vector<uint32_t>x,cmd,off;C4(std::string a):name(a),x(load(fs::path("inputs")/(a+".config.bin"))),cmd(load(fs::path("inputs")/(a+".commands.bin"))),off(load(fs::path("inputs")/(a+".offsets.bin"))){};};
struct Pool{uint32_t dt,n;Mem b,a;std::vector<uint32_t>aRef;Pool(uint32_t dtype,uint32_t features,bool check):dt(dtype),n(features),b(check?64ull*1024*1024:2ull*1024*1024*1024),a(256*(dt?4:2)),aRef(a.bytes/4){
 size_t rows=b.bytes/(n*(dt?4:2));
 if(dt){std::vector<float>v(b.bytes/4);for(size_t r=0;r<rows;r++)for(uint32_t j=0;j<n;j++)v[r*n+j]=r+1==rows?0:bv(r,j);b.put(v.data());}
 else{std::vector<uint16_t>v(b.bytes/2);for(size_t r=0;r<rows;r++)for(uint32_t j=0;j<n;j++)v[r*n+j]=h16(r+1==rows?0:bv(r,j));b.put(v.data());}
 uint32_t c0=dt?8:16;auto&raw=aRef;for(uint32_t m=0;m<16;m++)for(uint32_t k=0;k<16;k++){size_t index=(k/c0)*16*c0+m*c0+k%c0;float value=m==k?1.0f:0.0f;if(dt)std::memcpy((char*)raw.data()+index*4,&value,4);else{auto h=h16(value);std::memcpy((char*)raw.data()+index*2,&h,2);}}a.put(raw.data());
 }
 void audit(){
  std::vector<uint32_t>ar(aRef.size());ck(aclrtMemcpy(ar.data(),a.bytes,a.ptr(),a.bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(ar!=aRef)throw std::runtime_error("A input mutation");
  const size_t chunk=16*1024*1024;std::vector<uint32_t>raw(chunk/4);size_t es=dt?4:2;
  for(size_t offset=0;offset<b.bytes;offset+=chunk){size_t bytes=std::min(chunk,b.bytes-offset);ck(aclrtMemcpy(raw.data(),chunk,(char*)b.ptr()+offset,bytes,ACL_MEMCPY_DEVICE_TO_HOST));for(size_t j=0;j<bytes/es;j++){size_t logical=offset/es+j;auto want=logical/n+1==b.bytes/(n*es)?0:bv(logical/n,logical%n);if(dt){float got;std::memcpy(&got,(char*)raw.data()+j*4,4);if(got!=float(want))throw std::runtime_error("B input mutation");}else{uint16_t got;std::memcpy(&got,(char*)raw.data()+j*2,2);if(got!=h16(want))throw std::runtime_error("B input mutation");}}}
  a.guards();b.guards();
 }
};
uint64_t get64(const std::vector<uint32_t>&v,size_t i){return v[i]|(uint64_t(v[i+1])<<32);}
struct Run{
 C4&c;Pool&pool;std::vector<uint32_t>cfg,rows,wm;uint32_t blocks,wpc,capture;std::vector<uint32_t>bases,st;std::vector<float>y;Mem gcfg,gcmd,goff,grows,gwm,gbases,ring,out,stats;
 static uint32_t rounds(C4&c,bool check,uint32_t blocks){
  auto wm=load(fs::path("inputs")/(c.name+".windows.bin"));uint64_t u=0;for(size_t i=0;i<wm.size();i+=4)u+=wm[i+2];
  uint64_t all=check?std::max<uint64_t>(2*c.x[7],(blocks==1||std::getenv("M8_STRESS")?65:2)*blocks):uint64_t(c.x[11])*c.x[7]*(c.x[9]?1:4);
  if(!check){static std::map<std::string,uint32_t>mult=[](){std::map<std::string,uint32_t>m;std::ifstream f("batch-multipliers.txt");std::string s;uint32_t k;while(f>>s>>k){if(k<1||k>128)throw std::runtime_error("invalid multiplier");m[s]=k;}return m;}();auto it=mult.find(c.name);if(it!=mult.end())all*=it->second;}
  return uint32_t((all+blocks-1)/blocks);
 }
 Run(C4&cc,Pool&pp,bool check,uint32_t nb):c(cc),pool(pp),cfg(c.x),rows(load(fs::path("inputs")/(c.name+".rows.bin"))),wm(load(fs::path("inputs")/(c.name+".windows.bin"))),blocks(nb),wpc(rounds(c,check,nb)),capture(check),bases(size_t(wpc)*blocks),st(blocks*64),y(size_t(check?wpc*blocks*cfg[8]:blocks)*16*cfg[1]),gcfg(cfg.size()*4),gcmd(c.cmd.size()*4),goff(c.off.size()*4),grows(rows.size()*4),gwm(wm.size()*4),gbases(bases.size()*4),ring(size_t(blocks)*cfg[8]*16*cfg[1]*(cfg[0]?4:2)),out(y.size()*4),stats(st.size()*4){
  cfg[3]=capture;cfg[4]=wpc;cfg[5]=blocks;cfg[18]=pool.b.bytes/(cfg[1]*(cfg[0]?4:2))-1;
  uint32_t cap=cfg[17]?cfg[18]/2708:cfg[12]?(cfg[18]/cfg[14])*cfg[13]:cfg[18]/cfg[10];cap=std::min(cap,cfg[11]);if(!cap)throw std::runtime_error("empty capacity");
  for(uint32_t w=0;w<bases.size();w++){uint32_t index=(cfg[17]?w/cfg[7]:w)%cap;bases[w]=cfg[17]?index*2708:cfg[12]?(index/cfg[13])*cfg[14]+(index%cfg[13])*cfg[15]:index*cfg[10];if(bases[w]+cfg[10]>cfg[18])throw std::runtime_error("source extent");}
  gcfg.put(cfg.data());gcmd.put(c.cmd.data());goff.put(c.off.data());grows.put(rows.data());gwm.put(wm.data());gbases.put(bases.data());
 }
 struct Result{double us,event_us,reader_us,pack_us;uint64_t tiles,packcalls;};
 Result execute(aclrtStream stream){
  aclrtEvent a,b;ck(aclrtCreateEvent(&a));ck(aclrtCreateEvent(&b));ck(aclrtRecordEvent(a,stream));
  t8_launch(stream,pool.b.ptr(),gcfg.ptr(),gcmd.ptr(),goff.ptr(),grows.ptr(),gwm.ptr(),gbases.ptr(),pool.a.ptr(),ring.ptr(),out.ptr(),stats.ptr(),blocks);
  ck(aclrtRecordEvent(b,stream));ck(aclrtSynchronizeStream(stream));float elapsed;ck(aclrtEventElapsedTime(&elapsed,a,b));ck(aclrtDestroyEvent(a));ck(aclrtDestroyEvent(b));
  ck(aclrtMemcpy(y.data(),out.bytes,out.ptr(),out.bytes,ACL_MEMCPY_DEVICE_TO_HOST));ck(aclrtMemcpy(st.data(),stats.bytes,stats.ptr(),stats.bytes,ACL_MEMCPY_DEVICE_TO_HOST));
  uint64_t lo=~uint64_t(0),hi=0,reader=0,pack=0,tiles=0,packcalls=0;
  uint64_t expected=0;for(uint32_t w=0;w<bases.size();w++)expected+=wm[(w%cfg[7])*4+1];
  for(uint32_t k=0;k<blocks;k++){
   for(uint32_t side=0;side<(cfg[2]==2?2u:1u);side++){size_t ix=(side*blocks+k)*32;auto begin=get64(st,ix),end=get64(st,ix+2);if(end<=begin)throw std::runtime_error("timestamp order");lo=std::min(lo,begin);hi=std::max(hi,end);if(side){pack+=get64(st,ix+4);packcalls+=st[ix+6];}else{reader+=get64(st,ix+4);tiles+=st[ix+6];}}
   uint32_t start=capture?0:wpc-1;
   for(uint32_t i=start;i<wpc;i++){uint32_t w=i*blocks+k,wi=w%cfg[7],first=wm[wi*4],nt=wm[wi*4+1];
    for(uint32_t t=capture?0:nt-1;t<nt;t++)for(uint32_t row=0;row<16;row++)for(uint32_t n=0;n<cfg[1];n++){
     auto rr=rows[(first+t)*16+row];float want=rr==0xffffffff?0:bv(bases[w]+rr,n);size_t ix=((uint64_t(capture?w:0)*cfg[8]+t)*16+row)*cfg[1]+n;if(!capture)ix=(uint64_t(k)*16+row)*cfg[1]+n;
     if(y[ix]!=want)throw std::runtime_error("L1 identity mismatch w="+std::to_string(w)+" tile="+std::to_string(t)+" row="+std::to_string(row)+" feature="+std::to_string(n)+" got="+std::to_string(y[ix])+" expected="+std::to_string(want));
    }
   }
  }
  if(tiles!=expected||(cfg[2]==2&&packcalls!=expected*16))throw std::runtime_error("tile/row count mismatch");
  if(cfg[2]==2){std::vector<uint32_t>raw(ring.bytes/4);ck(aclrtMemcpy(raw.data(),ring.bytes,ring.ptr(),ring.bytes,ACL_MEMCPY_DEVICE_TO_HOST));for(uint32_t k=0;k<blocks;k++){uint32_t w=(wpc-1)*blocks+k,wi=w%cfg[7],first=wm[wi*4],nt=wm[wi*4+1];for(uint32_t t=0;t<nt;t++)for(uint32_t row=0;row<16;row++)for(uint32_t n=0;n<cfg[1];n++){auto rr=rows[(first+t)*16+row];float want=rr==0xffffffff?0:bv(bases[w]+rr,n);size_t ix=((uint64_t(k)*cfg[8]+t)*16+row)*cfg[1]+n;if(cfg[0]){float v;std::memcpy(&v,(char*)raw.data()+ix*4,4);if(v!=want)throw std::runtime_error("GM slot fp32 mismatch");}else{uint16_t v;std::memcpy(&v,(char*)raw.data()+ix*2,2);if(v!=h16(want))throw std::runtime_error("GM slot fp16 bit mismatch");}}}}
  for(auto p:{&gcfg,&gcmd,&goff,&grows,&gwm,&gbases,&ring,&out,&stats})p->guards();pool.b.guards();pool.a.guards();
  return {(hi-lo)/50.0,elapsed*1000.0,reader/50.0,pack/50.0,tiles,packcalls};
 }
 void audit(){for(auto p:{std::make_pair(&gcfg,&cfg),std::make_pair(&gcmd,&c.cmd),std::make_pair(&goff,&c.off),std::make_pair(&grows,&rows),std::make_pair(&gwm,&wm),std::make_pair(&gbases,&bases)}){std::vector<uint32_t>v(p.second->size());ck(aclrtMemcpy(v.data(),p.first->bytes,p.first->ptr(),p.first->bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(v!=*p.second)throw std::runtime_error("metadata mutation");}}
};
double med(std::vector<double>v){std::sort(v.begin(),v.end());return v[v.size()/2];}
int main(int argc,char**argv){try{
 if(argc<3)throw std::runtime_error("first|check|timeblock out [block] [list]");std::string mode=argv[1];fs::path root=argv[2];fs::create_directories(root);uint32_t block=argc>3?std::stoul(argv[3]):0;
 std::ifstream list(argc>4?argv[4]:"cases.list");std::string line;std::vector<C4>all;while(std::getline(list,line)){if(!line.empty()&&line.back()==13)line.pop_back();if(!line.empty())all.emplace_back(line);}if(all.empty())throw std::runtime_error("empty cases");
 std::map<std::pair<uint32_t,uint32_t>,std::vector<size_t>>groups;for(size_t i=0;i<all.size();i++)groups[{all[i].x[0],all[i].x[1]}].push_back(i);std::vector<std::pair<uint32_t,uint32_t>>keys;for(auto&p:groups)keys.push_back(p.first);std::mt19937 rng(20261115+block);if(mode=="timeblock")std::shuffle(keys.begin(),keys.end(),rng);
 ck(aclInit(nullptr));ck(aclrtSetDevice(0));ck(aclrtSetOpExecuteTimeOut(30));aclrtStream stream;ck(aclrtCreateStream(&stream));
 std::ofstream f(root/"timing.csv"),reg(root/"groups.csv");f<<std::setprecision(17)<<"case,block,windows_per_core,blocks,windows,tiles,pack_row_calls,us,event_us,us_per_window,reader_us_sum,pack_us_sum\n";reg<<std::setprecision(17)<<"dtype,N,before_us,after_us,drift,valid\n";size_t done=0;
 for(auto key:keys){Pool pool(key.first,key.second,mode!="timeblock");auto indices=groups[key];std::unique_ptr<Run>sentinel;double before=0,after=0;
  if(mode=="timeblock"){auto it=std::find_if(indices.begin(),indices.end(),[&](size_t i){auto&c=all[i];return c.name.find("u64-r16-")==0&&c.x[2]==2&&c.x[9];});if(it==indices.end())throw std::runtime_error("missing sentinel");sentinel=std::make_unique<Run>(all[*it],pool,false,24);sentinel->execute(stream);std::vector<double>v;for(int j=0;j<5;j++)v.push_back(sentinel->execute(stream).us);before=med(v);std::shuffle(indices.begin(),indices.end(),rng);}
  for(size_t index:indices){auto&c=all[index];fs::path dir=root/c.name;fs::create_directories(dir);try{Run run(c,pool,mode!="timeblock",mode=="first"?1:24);run.execute(stream);auto a=run.execute(stream);run.audit();uint64_t count=uint64_t(run.wpc)*run.blocks;f<<c.name<<","<<block<<","<<run.wpc<<","<<run.blocks<<","<<count<<","<<a.tiles<<","<<a.packcalls<<","<<a.us<<","<<a.event_us<<","<<a.us/count<<","<<a.reader_us<<","<<a.pack_us<<"\n";f.flush();dump(dir/"stats.bin",run.st.data(),run.stats.bytes);if(mode!="timeblock")dump(dir/"readback-f32.bin",run.y.data(),run.out.bytes);std::ofstream gate(dir/"gate.json");gate<<"{\"status\":\"PASS\",\"all_tiles\":"<<(run.capture?"true":"false")<<",\"last_slot_exact\":true,\"metadata_immutable\":true,\"guards\":true}";if(++done%12==0)std::cout<<"PASS "<<done<<"/"<<all.size()<<" "<<c.name<<std::endl;}catch(std::exception&e){std::ofstream(dir/"failure.txt")<<e.what();throw;}}
  if(sentinel){std::vector<double>v;for(int j=0;j<5;j++)v.push_back(sentinel->execute(stream).us);after=med(v);}pool.audit();double drift=sentinel?std::abs(after-before)/before:0;reg<<key.first<<","<<key.second<<","<<before<<","<<after<<","<<drift<<","<<(drift<=.05)<<"\n";reg.flush();std::cout<<"GROUP_COMPLETE "<<key.first<<" "<<key.second<<" drift="<<drift<<std::endl;
 }
 ck(aclrtDestroyStream(stream));ck(aclrtResetDevice(0));ck(aclFinalize());std::cout<<"M8_ALL_PASS "<<done<<" mode="<<mode<<std::endl;return 0;
 }catch(std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
