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
