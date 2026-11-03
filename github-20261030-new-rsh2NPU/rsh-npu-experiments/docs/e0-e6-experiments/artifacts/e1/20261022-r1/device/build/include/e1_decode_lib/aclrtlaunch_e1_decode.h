#ifndef HEADER_ACLRTLAUNCH_E1_DECODE_H
#define HEADER_ACLRTLAUNCH_E1_DECODE_H
#include "acl/acl_base.h"

#ifndef ACLRT_LAUNCH_KERNEL
#define ACLRT_LAUNCH_KERNEL(kernel_func) aclrtlaunch_##kernel_func
#endif

extern "C" uint32_t aclrtlaunch_e1_decode(uint32_t numBlocks, aclrtStream stream, void* dv, void* pv, void* jv, void* cv, void* av, void* rv, void* ov, void* zv);
#endif
