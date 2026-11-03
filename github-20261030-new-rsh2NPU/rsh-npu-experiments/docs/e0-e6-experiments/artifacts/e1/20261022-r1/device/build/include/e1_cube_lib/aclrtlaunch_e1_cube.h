#ifndef HEADER_ACLRTLAUNCH_E1_CUBE_H
#define HEADER_ACLRTLAUNCH_E1_CUBE_H
#include "acl/acl_base.h"

#ifndef ACLRT_LAUNCH_KERNEL
#define ACLRT_LAUNCH_KERNEL(kernel_func) aclrtlaunch_##kernel_func
#endif

extern "C" uint32_t aclrtlaunch_e1_cube(uint32_t numBlocks, aclrtStream stream, void* a, void* b, void* r, void* o, void* c, void* d);
#endif
