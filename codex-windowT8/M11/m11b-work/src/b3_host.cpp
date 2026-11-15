#include "identity-host-base.h"
#include <iomanip>
struct Case{std::string name;std::vector<uint32_t> cfg,cmd,off,rows,lengths;Case(std::string s):name(s),cfg(load(fs::path("inputs")/(s+".config.bin"))),cmd(load(fs::path("inputs")/(s+".commands.bin"))),off(load(fs::path("inputs")/(s+".offsets.bin"))),rows(load(fs::path("inputs")/(s+".rows.bin"))),lengths(load(fs::path("inputs")/(s+".lengths.bin"))){};};
struct Pool{
 uint32_t dt,n;Mem b,a;std::vector<uint32_t> aRef;
 Pool(uint32_t d,uint32_t f,bool check):dt(d),n(f),b(check?64ull*1024*1024:2ull*1024*1024*1024),a(256*(d?4:2)),aRef(a.bytes/4){
  size_t es=dt?4:2,rows=b.bytes/(n*es);std::vector<uint32_t> data(b.bytes/4);
  for(size_t r=0;r<rows;r++)for(uint32_t j=0;j<n;j++){float v=r>=rows-16?0:bv(r,j);if(dt)std::memcpy((char*)data.data()+(r*n+j)*4,&v,4);else{uint16_t h=v?h16(v):0;std::memcpy((char*)data.data()+(r*n+j)*2,&h,2);}}
  b.put(data.data());setA(0);
 }
 void setA(uint32_t mode){uint32_t c0=dt?8:16;for(uint32_t m=0;m<16;m++)for(uint32_t k=0;k<16;k++){size_t i=mode?k*16+m:(k/c0)*16*c0+m*c0+k%c0;float v=(m==(k+1)%16)?1:0;if(dt)std::memcpy((char*)aRef.data()+i*4,&v,4);else{auto h=h16(v);std::memcpy((char*)aRef.data()+i*2,&h,2);}}a.put(aRef.data());}
 void audit(){
  std::vector<uint32_t> ar(aRef.size());ck(aclrtMemcpy(ar.data(),a.bytes,a.ptr(),a.bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(ar!=aRef)throw std::runtime_error("A mutated");
  const size_t chunk=16*1024*1024;std::vector<uint32_t> raw(chunk/4);size_t es=dt?4:2,last=b.bytes/es-16*n;
  for(size_t off=0;off<b.bytes;off+=chunk){size_t bytes=std::min(chunk,b.bytes-off);ck(aclrtMemcpy(raw.data(),chunk,(char*)b.ptr()+off,bytes,ACL_MEMCPY_DEVICE_TO_HOST));for(size_t j=0;j<bytes/es;j++){size_t i=off/es+j;uint32_t want=i>=last?0:bv(i/n,i%n);if(dt){float got;std::memcpy(&got,(char*)raw.data()+j*4,4);if(got!=float(want))throw std::runtime_error("B mutated");}else{uint16_t got;std::memcpy(&got,(char*)raw.data()+j*2,2);if(got!=(want?h16(want):0))throw std::runtime_error("B mutated");}}}b.guards();a.guards();
 }
};
struct Run{
 Case& c;Pool& p;uint32_t blocks,cycles,capture,replicas;uint64_t sumU=0;std::vector<uint32_t>cfg,bases,st;std::vector<float>ref,y;std::unique_ptr<Mem>gc,gm,go,gb,out,stats;
 Run(Case&cc,Pool&pp,bool check,uint32_t cores):c(cc),p(pp),blocks(cores),capture(check),cfg(c.cfg),st(cores*32){
  uint32_t n=cfg[1],es=cfg[0]?4:2,span=cfg[12],wins=cfg[9];for(auto v:c.lengths)sumU+=v;
  uint64_t target=cfg[18]?1024ull*1024*1024:32ull*1024*1024;
  if(check)target=std::min<uint64_t>(target,8ull*1024*1024);
  uint32_t nonzeroRows=cfg[10]; // Exact selected-row working set per replica; no unselected gap counted.
  std::vector<uint32_t> selected;for(auto r:c.rows)if(r<0xffffff00)selected.push_back(r);std::sort(selected.begin(),selected.end());selected.erase(std::unique(selected.begin(),selected.end()),selected.end());
  replicas=std::max(1u,uint32_t((target+selected.size()*n*es-1)/(selected.size()*n*es)));
  replicas=std::min(replicas,uint32_t((p.b.bytes/(n*es)-16)/span));
  cycles=check?std::max(1u,(3*cfg[3]+cfg[2]-1)/cfg[2]):uint32_t(((wins>1?8ull:2ull)*1024*1024*1024+sumU*n*es*blocks-1)/(sumU*n*es*blocks));
  if(cfg[14]){cycles=1;capture=1;blocks=1;st.resize(32);cfg[3]=2;}
  cfg[5]=cycles;cfg[6]=blocks;cfg[7]=capture;cfg[21]=p.b.bytes/(n*es)-16;bases.resize(size_t(cycles)*blocks);for(size_t i=0;i<bases.size();i++)bases[i]=(i%replicas)*span;
  uint32_t outputs=capture?cycles*wins*blocks:blocks;ref.resize(size_t(outputs)*16*n);y.resize(ref.size());
  std::vector<size_t>starts(wins);size_t pos=0;for(uint32_t w=0;w<wins;w++){starts[w]=pos;pos+=(c.lengths[w]+15)/16*16;}
  for(uint32_t o=0;o<outputs;o++){uint32_t core=o%blocks,w=capture?(o/blocks)%wins:wins-1,epoch=capture?o/(blocks*wins):cycles-1,base=bases[epoch*blocks+core];
   for(uint32_t m=0;m<16;m++)for(uint32_t j=0;j<n;j++){uint32_t value=0;for(uint32_t k=0;k<c.lengths[w];k++){uint32_t r=c.rows[starts[w]+k];if(r>=0xffffff00)throw std::runtime_error("reference padding in valid range");value+=uint32_t(m==(k%16+1)%16)*bv(base+r,j);}ref[(size_t(o)*16+m)*n+j]=value;}
  }
  gc=std::make_unique<Mem>(cfg.size()*4);gm=std::make_unique<Mem>(c.cmd.size()*4);go=std::make_unique<Mem>(c.off.size()*4);gb=std::make_unique<Mem>(bases.size()*4);out=std::make_unique<Mem>(ref.size()*4);stats=std::make_unique<Mem>(st.size()*4);
  gc->put(cfg.data());gm->put(c.cmd.data());go->put(c.off.data());gb->put(bases.data());
 }
 double execute(aclrtStream stream,const fs::path&dir,bool save){
  t8_launch(stream,p.b.ptr(),gc->ptr(),gm->ptr(),go->ptr(),gb->ptr(),p.a.ptr(),out->ptr(),stats->ptr(),blocks);ck(aclrtSynchronizeStream(stream));
  ck(aclrtMemcpy(y.data(),out->bytes,out->ptr(),out->bytes,ACL_MEMCPY_DEVICE_TO_HOST));ck(aclrtMemcpy(st.data(),stats->bytes,stats->ptr(),stats->bytes,ACL_MEMCPY_DEVICE_TO_HOST));
  if(save){dump(dir/"output-f32.bin",y.data(),out->bytes);dump(dir/"reference-f32.bin",ref.data(),out->bytes);dump(dir/"stats.bin",st.data(),stats->bytes);}
  uint64_t lo=~uint64_t(0),hi=0;
  for(uint32_t b=0;b<blocks;b++){auto q=st.data()+b*32;uint64_t a=q[0]|(uint64_t(q[1])<<32),z=q[2]|(uint64_t(q[3])<<32);if(z<=a||(!cfg[14]&&(q[4]!=cycles*cfg[17]||q[5]!=cycles*cfg[2])))throw std::runtime_error("device counter mismatch");lo=std::min(lo,a);hi=std::max(hi,z);}
  for(size_t j=0;j<y.size();j++)if(y[j]!=ref[j])throw std::runtime_error("compute mismatch index="+std::to_string(j)+" got="+std::to_string(y[j])+" expected="+std::to_string(ref[j]));
  for(auto pair:{std::make_pair(gc.get(),&cfg),std::make_pair(gm.get(),&c.cmd),std::make_pair(go.get(),&c.off),std::make_pair(gb.get(),&bases)}){std::vector<uint32_t>got(pair.second->size());ck(aclrtMemcpy(got.data(),pair.first->bytes,pair.first->ptr(),pair.first->bytes,ACL_MEMCPY_DEVICE_TO_HOST));if(got!=*pair.second)throw std::runtime_error("metadata mutated");}
  for(auto q:{gc.get(),gm.get(),go.get(),gb.get(),out.get(),stats.get(),&p.b,&p.a})q->guards();return (hi-lo)/50.0;
 }
};
double med(std::vector<double>v){std::sort(v.begin(),v.end());return v[v.size()/2];}
int main(int argc,char**argv){try{
 if(argc<4)throw std::runtime_error("check|timeblock output list [block] [aMode]");std::string mode=argv[1];fs::path root=argv[2];fs::create_directories(root);uint32_t block=argc>4?std::stoul(argv[4]):0,aMode=argc>5?std::stoul(argv[5]):0;
 std::ifstream f(argv[3]);std::vector<Case>all;std::string line;while(std::getline(f,line))if(!line.empty())all.emplace_back(line);if(all.empty())throw std::runtime_error("empty cases");
 std::map<std::pair<uint32_t,uint32_t>,std::vector<size_t>>groups;for(size_t i=0;i<all.size();i++)groups[{all[i].cfg[0],all[i].cfg[1]}].push_back(i);std::vector<std::pair<uint32_t,uint32_t>>keys;for(auto&g:groups)keys.push_back(g.first);std::mt19937 rng(20261115+block);std::shuffle(keys.begin(),keys.end(),rng);
 ck(aclInit(nullptr));ck(aclrtSetDevice(0));ck(aclrtSetOpExecuteTimeOut(60));aclrtStream stream;ck(aclrtCreateStream(&stream));std::ofstream csv(root/"timing.csv"),reg(root/"group-registration.csv");csv<<std::setprecision(12);csv<<"case,block,a_mode,cycles,blocks,windows,sumU,replicas,source_pool_bytes,working_set_bytes,api_calls,us,us_per_matrix\n";reg<<"dtype,N,before_us,after_us,drift,valid,input_immutable\n";size_t done=0,failures=0;
 for(auto key:keys){Pool pool(key.first,key.second,mode!="timeblock");pool.setA(aMode);auto indices=groups[key];std::shuffle(indices.begin(),indices.end(),rng);for(auto i:indices)all[i].cfg[13]=aMode;
  std::unique_ptr<Run>sentinel;double before=0,after=0;if(mode=="timeblock"){auto i=indices[0];sentinel=std::make_unique<Run>(all[i],pool,false,24);sentinel->execute(stream,root,false);std::vector<double>v;for(int j=0;j<5;j++)v.push_back(sentinel->execute(stream,root,false));before=med(v);}
  for(auto i:indices){auto&c=all[i];fs::path dir=root/c.name;fs::create_directories(dir);try{Run r(c,pool,mode!="timeblock",mode=="check"?1:24);r.execute(stream,dir,true);double us=r.execute(stream,dir,true);
   uint64_t unique=r.replicas;std::vector<uint32_t>sel;for(auto q:c.rows)if(q<0xffffff00)sel.push_back(q);std::sort(sel.begin(),sel.end());sel.erase(std::unique(sel.begin(),sel.end()),sel.end());unique*=sel.size()*c.cfg[1]*(c.cfg[0]?4:2);
   csv<<c.name<<","<<block<<","<<aMode<<","<<r.cycles<<","<<r.blocks<<","<<c.cfg[9]<<","<<r.sumU<<","<<r.replicas<<","<<pool.b.bytes<<","<<unique<<","<<r.st[4]<<","<<us<<","<<us/(uint64_t(r.cycles)*r.blocks)<<"\n";csv.flush();std::ofstream gate(dir/"gate.json");gate<<"{\"status\":\"PASS\",\"exact_integer_float_reference\":true,\"metadata_immutable\":true,\"guards\":true}";std::cout<<"M11_PASS "<<++done<<"/"<<all.size()<<" "<<c.name<<std::endl;
  }catch(std::exception&e){std::ofstream err(dir/"failure.txt");err<<e.what();std::cerr<<c.name<<" "<<e.what()<<std::endl;failures++;}}
  if(sentinel){std::vector<double>v;for(int j=0;j<5;j++)v.push_back(sentinel->execute(stream,root,false));after=med(v);}pool.audit();double drift=sentinel?std::abs(after-before)/before:0;reg<<key.first<<","<<key.second<<","<<before<<","<<after<<","<<drift<<","<<(drift<=.05)<<",1\n";reg.flush();
 }
 ck(aclrtDestroyStream(stream));ck(aclrtResetDevice(0));ck(aclFinalize());std::cout<<"M11_ALL_PASS "<<done<<" failures="<<failures<<std::endl;return failures?1:0;
}catch(std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
