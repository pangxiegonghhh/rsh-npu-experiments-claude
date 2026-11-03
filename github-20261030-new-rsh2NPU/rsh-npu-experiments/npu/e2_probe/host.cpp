#include <acl/acl.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <stdexcept>
#include <algorithm>
#include <cstring>
#include <cstdlib>
namespace fs=std::filesystem;
static void check(aclError e,const char* phase){if(e!=ACL_SUCCESS){const char*msg=aclGetRecentErrMsg();throw std::runtime_error(std::string(phase)+" acl="+std::to_string(e)+" "+(msg?msg:""));}}
extern "C" void e2_launch(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);

#ifdef E0_DUAL
extern "C" void e0_launch_direct(void*,void*,void*,void*,void*,void*,void*);
#endif
static unsigned char guardByte=0x5a;
struct Guarded {
 static constexpr size_t guard=1024;void* base=nullptr;size_t payload;
 std::vector<unsigned char> initial;
 explicit Guarded(const std::vector<unsigned char>& data):payload(data.size()),initial(data.size()+guard*2,guardByte){
  std::copy(data.begin(),data.end(),initial.begin()+guard);
  check(aclrtMalloc(&base,initial.size(),ACL_MEM_MALLOC_HUGE_FIRST),"allocate");reset();
 }
 ~Guarded(){if(base)aclrtFree(base);}
 Guarded(const Guarded&)=delete;
 void* ptr(){return (unsigned char*)base+guard;}
 void reset(){check(aclrtMemcpy(base,initial.size(),initial.data(),initial.size(),ACL_MEMCPY_HOST_TO_DEVICE),"upload");}
 std::vector<unsigned char> read(){std::vector<unsigned char>x(initial.size());check(aclrtMemcpy(x.data(),x.size(),base,x.size(),ACL_MEMCPY_DEVICE_TO_HOST),"readback");return x;}
 void save(const fs::path& file){auto x=read();std::ofstream f(file,std::ios::binary);f.write((char*)x.data(),x.size());}
};
static std::vector<unsigned char> load(const fs::path&p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Missing "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
static uint32_t u32(const std::vector<unsigned char>&v,size_t p){if(p+4>v.size())throw std::runtime_error("u32 bounds");uint32_t x;std::memcpy(&x,v.data()+p,4);return x;}
static uint16_t u16(const std::vector<unsigned char>&v,size_t p){if(p+2>v.size())throw std::runtime_error("u16 bounds");return uint16_t(v[p])|(uint16_t(v[p+1])<<8);}
static void require(bool q,const char*msg){if(!q)throw std::runtime_error(msg);}
struct Input {
 std::vector<unsigned char>d,p,j,c,b;std::vector<size_t>values;uint32_t u,kp,n,np,orig,t,total=0;
 explicit Input(const fs::path&dir):d(load(dir/"desc.bin")),p(load(dir/"payload.bin")),j(load(dir/"cols.bin")),c(load(dir/"config.bin")),b(load(dir/"b.bin")){
  require(c.size()==32,"config length");u=u32(c,0);kp=u32(c,4);n=u32(c,8);np=u32(c,12);orig=u32(c,16);t=u32(c,20);
  require(u<=257&&orig>0&&orig<=4099&&u<=orig&&t==(u+15)/16&&kp==std::max(16u,t*16),"shape U/K");
  require(n>0&&n<=64&&np==((n+15)/16)*16,"shape N");
  require(d.size()==t*16&&u32(c,24)==d.size()&&u32(c,28)==p.size()&&j.size()==u*4,"directory length");
  require(b.size()==size_t(orig+1)*np*2,"B length");
  for(uint32_t i=0;i<u;++i){auto col=u32(j,i*4);require(col<orig&&(i==0||col>u32(j,(i-1)*4)),"column map");}
  size_t end=0;
  for(uint32_t tile=0;tile<t;++tile){
   uint64_t off=(uint64_t(u32(d,tile*16+4))<<32)|u32(d,tile*16);auto h=u32(d,tile*16+8);
   uint32_t z=h&65535,kind=(h>>16)&255,vk=h>>24,sz=u32(d,tile*16+12);
   require(z<=256&&(kind==1||kind==2)&&vk==std::min(16u,u-tile*16),"descriptor fields");
   require(off%32==0&&off==end&&off<=p.size()&&sz<=p.size()-off,"payload bounds/alignment");
   require(sz==(kind==0?512:kind==3?32*vk:kind==1?32+2*z:3*z+z%2),"payload length");
   std::vector<std::pair<uint32_t,size_t>> entries;
   if(kind==0||kind==3){
    for(uint32_t r=0;r<16;++r)for(uint32_t k=0;k<(kind==0?16:vk);++k){size_t at=off+2*(r*(kind==0?16:vk)+k);uint16_t v=u16(p,at);
     require((v&0x7c00)!=0x7c00,"nonfinite A");require(k<vk||v==0,"A tail nonzero");require(v!=0x8000,"signed zero");
     values.push_back(at);if(v&0x7fff)entries.push_back({r*16+k,at});
    }
   }else if(kind==1){
    for(uint32_t r=0;r<16;++r){auto mask=u16(p,off+r*2);require((mask>>vk)==0,"bitmap tail");
     for(uint32_t k=0;k<16;++k)if(mask&(1u<<k))entries.push_back({r*16+k,off+32+entries.size()*2});}
   }else{
    for(uint32_t q=0;q<z;++q){uint32_t pos=p[off+q];require(pos%16<vk&&(q==0||pos>p[off+q-1]),"index order/tail");
     entries.push_back({pos,off+z+z%2+q*2});}
    if(z%2)require(p[off+z]==0,"index prefix pad");
   }
   require(entries.size()==z,"nnz mismatch");
   if(kind==1||kind==2)for(auto e:entries){auto v=u16(p,e.second);require((v&0x7fff)!=0&&(v&0x7c00)!=0x7c00,"sparse value");values.push_back(e.second);}
   total+=z;end=(off+sz+31)/32*32;require(end<=p.size(),"aligned payload extent");
  }
  require(end==p.size(),"payload trailing bytes");
  for(size_t at=0;at<b.size();at+=2)require((u16(b,at)&0x7c00)!=0x7c00,"nonfinite B");
  for(uint32_t r=0;r<=orig;++r)for(uint32_t k=0;k<np;++k)if(r==orig||k>=n)require(u16(b,(size_t(r)*np+k)*2)==0,"B padding");
 }
};
static void intact(Guarded&g,const std::vector<unsigned char>&expect){auto x=g.read();
 require(std::equal(x.begin(),x.begin()+1024,g.initial.begin())&&std::equal(x.end()-1024,x.end(),g.initial.end()-1024),"input guard");
 require(std::equal(x.begin()+1024,x.end()-1024,expect.begin(),expect.end()),"input mutation");}
struct RunInput {
 std::vector<unsigned char>raw;uint32_t q,depth,rounds,capture,stall;
 explicit RunInput(const fs::path&p):raw(load(p/"run.bin")){
  require(raw.size()==20,"run length");q=u32(raw,0);depth=u32(raw,4);rounds=u32(raw,8);capture=u32(raw,12);stall=u32(raw,16);
  require((q==1||q==2||q==4||q==8)&&(depth==1||depth==2),"q/depth");
  require(rounds>=1&&rounds<=257&&capture<=1&&stall<=64,"rounds/capture/stall");
 }
};
static void one(const fs::path&input,const fs::path&output,int count,aclrtStream stream){
 Input x(input);RunInput run(input);fs::create_directories(output);
 Guarded desc(x.d),payload(x.p),cols(x.j),config(x.c),b(x.b),runc(run.raw);
 uint32_t packs=(x.t+run.q-1)/run.q;
 Guarded out(std::vector<unsigned char>(size_t(run.rounds)*16*x.np*4,0xef));
 Guarded snap(std::vector<unsigned char>(size_t(run.rounds)*std::max(1u,x.t)*512,0xab));
 Guarded trace(std::vector<unsigned char>(size_t(run.rounds)*std::max(1u,packs)*3*128,0xcd)),done(std::vector<unsigned char>(3*128,0xcd));
 for(int it=0;it<count;++it){
  auto pv=x.p,bv=x.b;
  if((it/2)%2)for(auto at:x.values)pv[at+1]^=0x80;
  if(it%2)for(size_t at=1;at<bv.size();at+=2)bv[at]^=0x80;
  std::copy(pv.begin(),pv.end(),payload.initial.begin()+1024);payload.reset();
  std::copy(bv.begin(),bv.end(),b.initial.begin()+1024);b.reset();out.reset();snap.reset();trace.reset();done.reset();
  e2_launch(stream,desc.ptr(),payload.ptr(),cols.ptr(),config.ptr(),b.ptr(),runc.ptr(),out.ptr(),snap.ptr(),trace.ptr(),done.ptr());
  check(aclrtSynchronizeStream(stream),"E2 mixed sync");
  auto suffix="-"+std::to_string(it)+".bin";
  out.save(output/("output"+suffix));snap.save(output/("snapshot"+suffix));trace.save(output/("trace"+suffix));done.save(output/("done"+suffix));
  intact(desc,x.d);intact(payload,pv);intact(cols,x.j);intact(config,x.c);intact(b,bv);intact(runc,run.raw);
  std::cout<<"CALL_OK "<<input.filename()<<" "<<it<<std::endl;
 }
 desc.save(output/"desc-after.bin");payload.save(output/"payload-after.bin");cols.save(output/"cols-after.bin");
 config.save(output/"config-after.bin");b.save(output/"b-after.bin");runc.save(output/"run-after.bin");
 std::ofstream meta(output/"host.json");meta<<"{\"status\":\"SYNC_OK\",\"iterations\":"<<count<<",\"guard_byte\":"<<unsigned(guardByte)<<",\"input_checked_each_call\":true,\"one_AIC_two_AIV\":true}";
}
int main(int argc,char**argv){
 try{
  require(argc>=3,"Usage: e2_runner --validate CASE | LIST OUTPUT [iterations]");
  if(std::string(argv[1])=="--validate"){Input a(argv[2]);RunInput r(argv[2]);std::cout<<"HOST_VALIDATED_NO_ACL"<<std::endl;return 0;}
  int count=argc>3?std::stoi(argv[3]):1;require(count>=1&&count<=10,"repeat count");
  if(const char*gb=std::getenv("E2_GUARD_BYTE"))guardByte=(unsigned char)std::stoul(gb,nullptr,0);
  std::ifstream list(argv[1]);require(bool(list),"list missing");std::vector<fs::path>paths;std::string line;
  while(std::getline(list,line))if(!line.empty()){Input a(line);RunInput r(line);paths.emplace_back(line);}
  require(!paths.empty(),"empty list");
  check(aclInit(nullptr),"init");check(aclrtSetDevice(0),"device");aclrtStream s;check(aclrtCreateStream(&s),"stream");
  for(auto p:paths)one(p,fs::path(argv[2])/p.filename(),count,s);
  check(aclrtDestroyStream(s),"destroy");check(aclrtResetDevice(0),"reset");check(aclFinalize(),"finalize");
  std::cout<<"BATCH_OK "<<paths.size()<<std::endl;return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}
}
