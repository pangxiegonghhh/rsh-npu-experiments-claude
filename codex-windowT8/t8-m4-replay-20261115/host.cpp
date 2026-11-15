#include "host-base.h"

struct ReplayRun {
 C4& c; Pool& pool; uint32_t blocks,cycles,capture,zeroRow;
 std::vector<uint32_t> cfg,bases,st;
 std::vector<std::vector<uint32_t>> columns;
 std::vector<float> ref,y;
 std::unique_ptr<Mem> gc,gm,go,gb,out,stats;
 uint64_t sumU=0;
 ReplayRun(C4& cc,Pool& pp,bool check,uint32_t b):c(cc),pool(pp),blocks(b),capture(check),cfg(c.x),st(b*32) {
  const uint32_t n=cfg[1],es=cfg[0]?4:2,windows=cfg[9];
  zeroRow=pool.b.bytes/(n*es)-16;cfg[10]=zeroRow;
  columns.resize(windows);
  for(uint32_t t=0;t<cfg[2];t++){
   uint32_t w=cfg[24+t*3],tile=cfg[24+t*3+1];
   for(uint32_t j=c.off[t];j<c.off[t+1];j++){
    auto p=c.cmd.data()+j*8;if(p[6])continue;
    for(uint32_t m=0;m<p[2];m++)for(uint32_t k=0;k<p[1];k++){
     uint32_t ix=tile*16+p[4]+m*p[1]+k;
     if(columns[w].size()<=ix)columns[w].resize(ix+1);
     columns[w][ix]=p[0]+m*p[3]+k;
    }
   }
  }
  for(auto& v:columns)sumU+=v.size();
  cycles=check?std::max(1u,(3*cfg[3]+cfg[2]-1)/cfg[2]):uint32_t((8ull*1024*1024*1024+sumU*n*es*blocks-1)/(sumU*n*es*blocks));
  cfg[5]=cycles;cfg[6]=blocks;cfg[7]=capture;
  bases.resize(size_t(cycles)*blocks);
  for(size_t i=0;i<bases.size();i++){
   bases[i]=(i%cfg[12])*cfg[13];
   if(uint64_t(bases[i]+cfg[13])*n*es>uint64_t(zeroRow)*n*es)throw std::runtime_error("replay source extent");
  }
  ref.resize(size_t(check?cycles*windows*blocks:blocks)*16*n);y.resize(ref.size());
  for(uint32_t o=0;o<(check?cycles*windows*blocks:blocks);o++){
   uint32_t core=o%blocks,window=check?(o/blocks)%windows:windows-1,epoch=check?o/(blocks*windows):cycles-1;
   uint32_t base=bases[epoch*blocks+core];
   for(uint32_t m=0;m<16;m++)for(uint32_t j=0;j<n;j++){
    uint32_t sum=0;for(uint32_t k=0;k<columns[window].size();k++)sum+=(1+(m*3+(k%16)*5)%7)*bv(base+columns[window][k],j);
    ref[(size_t(o)*16+m)*n+j]=sum;
   }
  }
  gc=std::make_unique<Mem>(cfg.size()*4);gm=std::make_unique<Mem>(c.cmd.size()*4);go=std::make_unique<Mem>(c.off.size()*4);gb=std::make_unique<Mem>(bases.size()*4);out=std::make_unique<Mem>(ref.size()*4);stats=std::make_unique<Mem>(st.size()*4);
  gc->put(cfg.data());gm->put(c.cmd.data());go->put(c.off.data());gb->put(bases.data());
 }
 double execute(aclrtStream stream){
  t8_launch(stream,pool.b.ptr(),gc->ptr(),gm->ptr(),go->ptr(),gb->ptr(),pool.a.ptr(),out->ptr(),stats->ptr(),blocks);
  ck(aclrtSynchronizeStream(stream));ck(aclrtMemcpy(y.data(),out->bytes,out->ptr(),out->bytes,ACL_MEMCPY_DEVICE_TO_HOST));ck(aclrtMemcpy(st.data(),stats->bytes,stats->ptr(),stats->bytes,ACL_MEMCPY_DEVICE_TO_HOST));
  uint64_t lo=~uint64_t(0),hi=0;
  for(uint32_t k=0;k<blocks;k++){
   uint64_t a=st[k*32]|(uint64_t(st[k*32+1])<<32),b=st[k*32+2]|(uint64_t(st[k*32+3])<<32);
   if(b<=a||st[k*32+4]!=cycles*cfg[8]||st[k*32+5]!=cycles*cfg[2])throw std::runtime_error("replay counter mismatch");
   lo=std::min(lo,a);hi=std::max(hi,b);
  }
  for(size_t j=0;j<y.size();j++)if(y[j]!=ref[j])throw std::runtime_error("replay compute mismatch element="+std::to_string(j)+" got="+std::to_string(y[j])+" expected="+std::to_string(ref[j]));
  for(auto p:{gc.get(),gm.get(),go.get(),gb.get(),out.get(),stats.get(),&pool.b,&pool.a})p->guards();
  return (hi-lo)/50.0;
 }
 void metadataAudit(){
  for(auto pair:{std::make_pair(gc.get(),&cfg),std::make_pair(gm.get(),&c.cmd),std::make_pair(go.get(),&c.off),std::make_pair(gb.get(),&bases)}){
   std::vector<uint32_t> got(pair.second->size());ck(aclrtMemcpy(got.data(),pair.first->bytes,pair.first->ptr(),pair.first->bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(got!=*pair.second)throw std::runtime_error("replay metadata mutation");
  }
 }
};

void zeroTail(Pool& p){
 size_t n=16*p.n*(p.dt?4:2);std::vector<uint8_t> z(n,0);
 ck(aclrtMemcpy((char*)p.b.ptr()+p.b.bytes-n,n,z.data(),n,ACL_MEMCPY_HOST_TO_DEVICE));
}
void auditReplayPool(Pool& p){
 std::vector<uint32_t> ar(p.aRef.size());ck(aclrtMemcpy(ar.data(),p.a.bytes,p.a.ptr(),p.a.bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(ar!=p.aRef)throw std::runtime_error("replay A mutation");
 const size_t chunk=16*1024*1024;std::vector<uint32_t> raw(chunk/4);size_t es=p.dt?4:2,last=p.b.bytes/es-16*p.n;
 for(size_t offset=0;offset<p.b.bytes;offset+=chunk){
  size_t bytes=std::min(chunk,p.b.bytes-offset);ck(aclrtMemcpy(raw.data(),chunk,(char*)p.b.ptr()+offset,bytes,ACL_MEMCPY_DEVICE_TO_HOST));
  for(size_t j=0;j<bytes/es;j++){
   size_t i=offset/es+j;uint32_t want=i>=last?0:bv(i/p.n,i%p.n);
   if(p.dt){float got;std::memcpy(&got,(char*)raw.data()+j*4,4);if(got!=float(want))throw std::runtime_error("replay B mutation");}
   else{uint16_t got;std::memcpy(&got,(char*)raw.data()+j*2,2);if(got!=(want?h16(want):0))throw std::runtime_error("replay B mutation");}
  }
 }
 p.b.guards();p.a.guards();
}

int main(int argc,char**argv){try{
 if(argc<3)throw std::runtime_error("first|check|timeblock output [block] [list]");
 std::string mode=argv[1];fs::path root=argv[2];fs::create_directories(root);uint32_t block=argc>3?std::stoul(argv[3]):0;
 std::ifstream list(argc>4?argv[4]:"cases.list");std::vector<C4> all;std::string line;
 while(std::getline(list,line)){if(!line.empty()&&line.back()==13)line.pop_back();if(!line.empty())all.emplace_back(line);}
 if(mode=="first")all.erase(std::remove_if(all.begin(),all.end(),[](const C4& c){return (c.x[1]!=16&&c.x[1]!=256)||c.x[11]!=0;}),all.end());
 if(all.empty())throw std::runtime_error("empty replay list");
 std::map<std::pair<uint32_t,uint32_t>,std::vector<size_t>> groups;for(size_t i=0;i<all.size();i++)groups[{all[i].x[0],all[i].x[1]}].push_back(i);
 std::vector<std::pair<uint32_t,uint32_t>> keys;for(auto& x:groups)keys.push_back(x.first);std::mt19937 rng(20261115+block);if(mode=="timeblock")std::shuffle(keys.begin(),keys.end(),rng);
 ck(aclInit(nullptr));ck(aclrtSetDevice(0));ck(aclrtSetOpExecuteTimeOut(15));aclrtStream stream;ck(aclrtCreateStream(&stream));
 std::ofstream csv(root/"timing.csv"),reg(root/"group-registration.csv");csv<<"case,block,cycles_per_core,blocks,windows_per_cycle,useful_rows_per_cycle,api_calls_per_cycle,us,us_per_matrix\n";reg<<"dtype,N,block,before_us,after_us,drift,valid,input_immutable\n";size_t done=0;
 for(auto key:keys){
  Pool pool(key.first,key.second,mode!="timeblock");zeroTail(pool);auto indices=groups[key];std::unique_ptr<ReplayRun> sentinel;double before=0,after=0;
  if(mode=="timeblock"){
   auto i=std::find_if(indices.begin(),indices.end(),[&](size_t j){return all[j].name.find("cora-B0-")==0&&all[j].x[11]==1;});if(i==indices.end())throw std::runtime_error("replay sentinel missing");
   sentinel=std::make_unique<ReplayRun>(all[*i],pool,false,24);sentinel->execute(stream);std::vector<double> v;for(int j=0;j<5;j++)v.push_back(sentinel->execute(stream));before=med(v);std::shuffle(indices.begin(),indices.end(),rng);
  }
  for(auto i:indices){auto& c=all[i];fs::path dir=root/c.name;fs::create_directories(dir);try{
   ReplayRun r(c,pool,mode!="timeblock",mode=="first"?1:24);r.execute(stream);double us=r.execute(stream);r.metadataAudit();
   csv<<c.name<<","<<block<<","<<r.cycles<<","<<r.blocks<<","<<c.x[9]<<","<<r.sumU<<","<<c.x[8]<<","<<us<<","<<us/(uint64_t(r.cycles)*r.blocks)<<"\n";csv.flush();dump(dir/"stats.bin",r.st.data(),r.stats->bytes);
   if(mode!="timeblock"){dump(dir/"output-f32.bin",r.y.data(),r.out->bytes);dump(dir/"reference-f32.bin",r.ref.data(),r.out->bytes);}
   std::ofstream gate(dir/"gate.json");gate<<"{\"status\":\"PASS\",\"all_window_capture\":"<<(r.capture?"true":"false")<<",\"last_window_per_core\":true,\"metadata_immutable\":true,\"guards\":true}";
   std::cout<<"REPLAY_PASS "<<++done<<"/"<<all.size()<<" "<<c.name<<std::endl;
  }catch(std::exception& e){std::ofstream f(dir/"failure.txt");f<<e.what();throw;}}
  if(sentinel){std::vector<double> v;for(int j=0;j<5;j++)v.push_back(sentinel->execute(stream));after=med(v);}
  auditReplayPool(pool);double drift=sentinel?std::abs(after-before)/before:0;reg<<key.first<<","<<key.second<<","<<block<<","<<before<<","<<after<<","<<drift<<","<<(drift<=.05)<<",1\n";reg.flush();
 }
 ck(aclrtDestroyStream(stream));ck(aclrtResetDevice(0));ck(aclFinalize());std::cout<<"REPLAY_ALL_PASS "<<done<<" mode="<<mode<<std::endl;return 0;
}catch(std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}}
