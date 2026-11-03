#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <stdexcept>
#include <algorithm>
#include <cstring>
#include <cstdint>
namespace fs=std::filesystem;
static std::vector<unsigned char> load(const fs::path&p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Missing "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
static uint32_t u32(const std::vector<unsigned char>&v,size_t p){if(p+4>v.size())throw std::runtime_error("u32 bounds");uint32_t x;std::memcpy(&x,v.data()+p,4);return x;}
static uint16_t u16(const std::vector<unsigned char>&v,size_t p){if(p+2>v.size())throw std::runtime_error("u16 bounds");return uint16_t(v[p])|(uint16_t(v[p+1])<<8);}
static void require(bool q,const char*msg){if(!q)throw std::runtime_error(msg);}
struct Input {
 std::vector<unsigned char>d,p,j,c,b;std::vector<size_t>values;uint32_t u,kp,n,np,orig,t,total=0;
 explicit Input(const fs::path&dir):d(load(dir/"desc.bin")),p(load(dir/"payload.bin")),j(load(dir/"cols.bin")),c(load(dir/"config.bin")),b(load(dir/"b.bin")){
  require(c.size()==32,"config length");u=u32(c,0);kp=u32(c,4);n=u32(c,8);np=u32(c,12);orig=u32(c,16);t=u32(c,20);
  require(u<=64&&orig>0&&orig<=4099&&u<=orig&&t==(u+15)/16&&kp==std::max(16u,t*16),"shape U/K");
  require(n>0&&n<=64&&np==((n+15)/16)*16,"shape N");
  require(d.size()==t*16&&u32(c,24)==d.size()&&u32(c,28)==p.size()&&j.size()==u*4,"directory length");
  require(b.size()==size_t(orig+1)*np*2,"B length");
  for(uint32_t i=0;i<u;++i){auto col=u32(j,i*4);require(col<orig&&(i==0||col>u32(j,(i-1)*4)),"column map");}
  size_t end=0;
  for(uint32_t tile=0;tile<t;++tile){
   uint64_t off=(uint64_t(u32(d,tile*16+4))<<32)|u32(d,tile*16);auto h=u32(d,tile*16+8);
   uint32_t z=h&65535,kind=(h>>16)&255,vk=h>>24,sz=u32(d,tile*16+12);
   require(z<=256&&kind<=3&&vk==std::min(16u,u-tile*16),"descriptor fields");
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

int main(int c,char**v){try{for(int i=1;i<c;++i){Input x(v[i]);}return 0;}catch(const std::exception&e){std::cerr<<e.what();return 1;}}
