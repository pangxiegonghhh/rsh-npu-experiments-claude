#ifndef HEADER_ACLRTLAUNCH_E2_MIX_H
#define HEADER_ACLRTLAUNCH_E2_MIX_H
#include "acl/acl_base.h"

#ifndef ACLRT_LAUNCH_KERNEL
#define ACLRT_LAUNCH_KERNEL(kernel_func) aclrtlaunch_##kernel_func
#endif

extern "C" uint32_t aclrtlaunch_e2_mix(uint32_t numBlocks, aclrtStream stream, void* dv, void* pv, void* jv, void* cv, void* bv, void* runv, void* ov, void* snapv, void* tracev, void* donev);
#endif
