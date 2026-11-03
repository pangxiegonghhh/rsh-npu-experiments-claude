#include "work.h"
extern "C" __global__ __aicore__ void rsh_cube(GM_ADDR ptr,GM_ADDR cols,GM_ADDR vals,GM_ADDR gp,GM_ADDR refs,GM_ADDR tiles,GM_ADDR rows,GM_ADDR rhs,GM_ADDR packed,GM_ADDR output,GM_ADDR config) {
    KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_AIC_ONLY);
    RshConfig c=LoadConfig(config);
    if(c.groups){CubeWork op;op.Init(gp,refs,tiles,rhs,packed,c);op.Process();}
}
extern "C" void rsh_launch_cube(void* stream,int blocks,void* ptr,void* cols,void* vals,void* gp,void* refs,void* tiles,void* rows,void* rhs,void* packed,void* output,void* config) {
 rsh_cube<<<blocks,nullptr,stream>>>((GM_ADDR)ptr,(GM_ADDR)cols,(GM_ADDR)vals,(GM_ADDR)gp,(GM_ADDR)refs,(GM_ADDR)tiles,(GM_ADDR)rows,(GM_ADDR)rhs,(GM_ADDR)packed,(GM_ADDR)output,(GM_ADDR)config);
}
