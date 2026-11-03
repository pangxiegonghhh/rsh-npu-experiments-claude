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
extern "C" void e0_launch(void*,void*,void*,void*,void*,void*,void*);
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
int main(int argc,char**argv){
 try{
  if(argc<3)throw std::runtime_error("Usage: e0_MODE CASE_DIR OUTPUT_DIR [direct] [iterations]");
  if(const char* gb=std::getenv("E0_GUARD_BYTE"))guardByte=(unsigned char)std::stoul(gb,nullptr,0);
  fs::path input=argv[1],output=argv[2];fs::create_directories(output);
  auto cv=load(input/"config.bin");if(cv.size()!=48)throw std::runtime_error("Bad config bytes");
  int c[12];std::memcpy(c,cv.data(),48);
  if(c[0]<1||c[1]<1||c[2]<1||c[3]%16||c[4]%16||c[5]%16||c[3]<c[0]||c[4]<c[1]||c[5]<c[2]||c[3]>32||c[4]>80||c[5]>64)throw std::runtime_error("Unsafe shape");
  auto av=load(input/((argc>3&&std::string(argv[3])=="direct")?"a-direct.bin":"a.bin")),bv=load(input/"b.bin"),rv=load(input/"refs.bin");
  if(rv.size()!=size_t(c[4])*4||bv.size()%(c[5]*2))throw std::runtime_error("Unsafe source size");
  for(int i=0;i<c[4];++i){int r;std::memcpy(&r,rv.data()+i*4,4);if(r<0||size_t(r)>=bv.size()/(c[5]*2))throw std::runtime_error("Unsafe B row");}
  if(av.size()!=size_t(c[3])*(c[8]?c[8]:c[4])*2)throw std::runtime_error("Unsafe A size");
  check(aclInit(nullptr),"init");check(aclrtSetDevice(0),"device");aclrtStream stream;check(aclrtCreateStream(&stream),"stream");
  {
   Guarded a(av),b(bv),refs(rv),config(cv);
   std::vector<float> markers(c[3]*c[5],12345.0f);std::vector<unsigned char> ox(markers.size()*4);std::memcpy(ox.data(),markers.data(),ox.size());
   Guarded out(ox),debug(std::vector<unsigned char>(16,0));int count=argc>4?std::stoi(argv[4]):1;
   if(count<1||count>100)throw std::runtime_error("Unsafe repeat count");
   for(int iter=0;iter<count;++iter){
    auto av2=av;if((iter/2)%2)for(size_t i=1;i<av2.size();i+=2)av2[i]^=0x80;
    std::copy(av2.begin(),av2.end(),a.initial.begin()+1024);a.reset();
    auto bv2=bv;if(iter%2)for(size_t i=1;i<bv2.size();i+=2)bv2[i]^=0x80;
    std::copy(bv2.begin(),bv2.end(),b.initial.begin()+1024);b.reset();out.reset();debug.reset();
#ifdef E0_DUAL
    if(argc>3&&std::string(argv[3])=="direct")e0_launch_direct(stream,a.ptr(),b.ptr(),refs.ptr(),out.ptr(),config.ptr(),debug.ptr());else
#endif
    e0_launch(stream,a.ptr(),b.ptr(),refs.ptr(),out.ptr(),config.ptr(),debug.ptr());
    std::cout<<"launch_submitted iteration="<<iter<<std::endl;
    check(aclrtSynchronizeStream(stream),"sync");
    out.save(output/("output-"+std::to_string(iter)+".bin"));debug.save(output/("debug-"+std::to_string(iter)+".bin"));
   }
   a.save(output/"a-after.bin");b.save(output/"b-after.bin");refs.save(output/"refs-after.bin");config.save(output/"config-after.bin");
   std::ofstream meta(output/"host.json");meta<<"{\"status\":\"SYNC_OK\",\"iterations\":"<<count<<",\"guard_byte\":"<<unsigned(guardByte)<<",\"gm_a_address_mod512\":"<<(uintptr_t(a.ptr())%512)<<"}";
  }
  check(aclrtDestroyStream(stream),"destroy");check(aclrtResetDevice(0),"reset");check(aclFinalize(),"finalize");
  std::cout<<"PASS host launch/sync/readback"<<std::endl;return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}
}
