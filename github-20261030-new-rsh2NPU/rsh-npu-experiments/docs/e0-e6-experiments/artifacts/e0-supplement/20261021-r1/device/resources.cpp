#include <acl/acl.h>
#include "platform/platform_info.h"
#include "tiling/platform/platform_ascendc.h"
#include <iostream>
int main(){
 aclInit(nullptr);aclrtSetDevice(0);
 const char* soc=aclrtGetSocName();std::cout<<"detected_soc="<<(soc?soc:"null")<<std::endl;
 auto& mgr=fe::PlatformInfoManager::GeInstance();
 auto init=mgr.InitializePlatformInfo();fe::PlatFormInfos info;fe::OptionalInfos opt;
 auto rc=mgr.GetPlatformInfos(soc?soc:"Ascend910B2",info,opt);
 std::cout<<"platform_init="<<init<<" platform_query="<<rc<<std::endl;if(rc)return 1;
 platform_ascendc::PlatformAscendC p(&info);
 for(auto v:{platform_ascendc::CoreMemType::L1,platform_ascendc::CoreMemType::L0_A,platform_ascendc::CoreMemType::L0_B,platform_ascendc::CoreMemType::L0_C,platform_ascendc::CoreMemType::UB}){uint64_t bytes=0;p.GetCoreMemSize(v,bytes);std::cout<<int(v)<<" "<<bytes<<std::endl;}
 aclrtResetDevice(0);aclFinalize();
}
