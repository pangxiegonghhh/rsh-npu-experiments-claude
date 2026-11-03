// Reuse the already validated guarded Case implementation without changing it.
#define main e0_guarded_original_main
#include "../runner_guarded.cpp"
#undef main
int main(int argc,char**argv){
 try{
  if(argc!=3)throw std::runtime_error("Usage: repeat_each INPUT_ROOT OUTPUT_ROOT");
  fs::path input=argv[1],outRoot=argv[2];fs::create_directories(outRoot);
  check(aclInit(nullptr));check(aclrtSetDevice(0));aclrtStream stream;check(aclrtCreateStream(&stream));
  std::ofstream trace(outRoot/"trace.json");trace<<"{\"schema\":\"e0-each-call-v1\",\"records\":[";int count=0;
  for(const char* name:{"M30_K70_N40","ADJACENT_U17_U37_N33"}){
   Case item(input/name/"V1",1);
   std::vector<uint16_t> original((size_t)item.c.blocks*256);
   std::ifstream file(input/name/"V1"/"tiles.bin",std::ios::binary);file.read((char*)original.data(),original.size()*2);
   if(!file)throw std::runtime_error("Missing A tiles");
   for(int iteration=0;iteration<10;++iteration){
    bool negativeA=(iteration/2)%2,negativeB=iteration%2;auto tiles=original;
    if(negativeA)for(auto& x:tiles)x^=0x8000;
    check(aclrtMemcpy(item.tiles->device,item.tiles->size,tiles.data(),tiles.size()*2,ACL_MEMCPY_HOST_TO_DEVICE));
    captureRoot=outRoot/name/("iteration-"+std::to_string(iteration));
    item.call(stream,negativeB);item.validate(negativeA^negativeB);
    if(item.maxError!=0)throw std::runtime_error("Nonzero exact-case error");
    if(count++)trace<<',';
    trace<<"{\"case_id\":\""<<name<<"\",\"iteration\":"<<iteration<<",\"negative_a\":"<<int(negativeA)<<",\"negative_b\":"<<int(negativeB)<<",\"max_abs_error\":0,\"packed_checked\":true,\"padding_checked\":true,\"guards_checked\":true,\"status\":\"PASS\"}";
    trace.flush();
   }
  }
  trace<<"],\"call_count\":"<<count<<",\"status\":\"PASS\"}\n";trace.close();
  check(aclrtDestroyStream(stream));check(aclrtResetDevice(0));check(aclFinalize());
  std::cout<<"PASS "<<count<<" calls; each checked and captured"<<std::endl;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}
}

