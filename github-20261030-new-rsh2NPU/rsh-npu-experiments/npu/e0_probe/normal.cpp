#include "probe.h"
extern "C" __global__ __aicore__ void e0_normal(GM_ADDR a,GM_ADDR b,GM_ADDR r,GM_ADDR o,GM_ADDR c,GM_ADDR d){
 KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_AIC_ONLY);Probe<false> p;p.Run(a,b,r,o,c,d);
}
extern "C" void e0_launch(void* s,void* a,void* b,void* r,void* o,void* c,void* d){
 e0_normal<<<1,nullptr,s>>>((GM_ADDR)a,(GM_ADDR)b,(GM_ADDR)r,(GM_ADDR)o,(GM_ADDR)c,(GM_ADDR)d);
}
