// Frozen E0 primitive; no cross-kernel shared-memory protocol in E1.
#include "../e0_probe/probe.h"
extern "C" __global__ __aicore__ void e1_cube(GM_ADDR a,GM_ADDR b,GM_ADDR r,GM_ADDR o,GM_ADDR c,GM_ADDR d){
 KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_AIC_ONLY);Probe<false> p;p.Run(a,b,r,o,c,d);
}
extern "C" void e1_launch_cube(void*s,void*a,void*b,void*r,void*o,void*c,void*d){
 e1_cube<<<1,nullptr,s>>>((GM_ADDR)a,(GM_ADDR)b,(GM_ADDR)r,(GM_ADDR)o,(GM_ADDR)c,(GM_ADDR)d);
}
