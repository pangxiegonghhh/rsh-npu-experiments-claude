#include <acl/acl.h>
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
static void check(aclError e){if(e!=ACL_SUCCESS)throw std::runtime_error("ACL error "+std::to_string(e));}
extern "C" void rsh_launch_zero(void*,int,void*,uint64_t);
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("Usage: zero_probe OUTPUT_JSON");
 check(aclInit(nullptr));check(aclrtSetDevice(0));aclrtStream stream;check(aclrtCreateStream(&stream));
 std::vector<uint64_t> sizes={0,16,32,8176,8192,8208,16368,16384,16400,5242896};int tests=0;
 for(int cores:{1,48})for(auto n:sizes)for(int round=0;round<2;++round){
  constexpr size_t guard=16;uint32_t pattern=round?0x7fc12345:0x3f800001;
  std::vector<uint32_t> host(n+guard*2,pattern);void* p=nullptr;size_t bytes=host.size()*4;
  check(aclrtMalloc(&p,bytes,ACL_MEM_MALLOC_HUGE_FIRST));check(aclrtMemcpy(p,bytes,host.data(),bytes,ACL_MEMCPY_HOST_TO_DEVICE));
  rsh_launch_zero(stream,cores,(char*)p+guard*4,n);check(aclrtSynchronizeStream(stream));check(aclrtMemcpy(host.data(),bytes,p,bytes,ACL_MEMCPY_DEVICE_TO_HOST));
  for(size_t j=0;j<host.size();++j){uint32_t wanted=(j>=guard&&j<guard+n)?0:pattern;if(host[j]!=wanted)throw std::runtime_error("guard/value failure size="+std::to_string(n)+" at="+std::to_string(j));}
  check(aclrtFree(p));++tests;
 }
 std::ofstream f(argv[1]);f<<"{\"passed\":true,\"tests\":"<<tests<<",\"cores\":[1,48],\"poison_patterns\":[\"finite_nonzero\",\"NaN\"],\"sizes_floats\":[0,16,32,8176,8192,8208,16368,16384,16400,5242896],\"guard_floats_each_side\":16,\"expected_bits\":0,\"both_guards_unchanged\":true}\n";
 check(aclrtDestroyStream(stream));check(aclrtResetDevice(0));check(aclFinalize());std::cout<<"ZERO_PROBE_PASS "<<tests<<std::endl;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}return 0;
}
