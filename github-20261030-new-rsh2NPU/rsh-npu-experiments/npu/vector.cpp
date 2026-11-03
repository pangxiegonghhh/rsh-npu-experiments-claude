#include "work.h"
extern "C" __global__ __aicore__ void rsh_vector(GM_ADDR ptr,GM_ADDR cols,GM_ADDR vals,GM_ADDR gp,GM_ADDR refs,GM_ADDR tiles,GM_ADDR rows,GM_ADDR rhs,GM_ADDR packed,GM_ADDR output,GM_ADDR config) {
    KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_AIV_ONLY);
    RshConfig c=LoadConfig(config);
    VectorWork op;op.Init(ptr,cols,vals,rhs,rows,output,c,c.cores*2);op.Process();
}
extern "C" void rsh_launch_vector(void* stream,int blocks,void* ptr,void* cols,void* vals,void* gp,void* refs,void* tiles,void* rows,void* rhs,void* packed,void* output,void* config) {
 rsh_vector<<<blocks,nullptr,stream>>>((GM_ADDR)ptr,(GM_ADDR)cols,(GM_ADDR)vals,(GM_ADDR)gp,(GM_ADDR)refs,(GM_ADDR)tiles,(GM_ADDR)rows,(GM_ADDR)rhs,(GM_ADDR)packed,(GM_ADDR)output,(GM_ADDR)config);
}
