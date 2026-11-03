#include "work.h"
extern "C" __global__ __aicore__ void rsh_restore(GM_ADDR packed,GM_ADDR map,GM_ADDR output,GM_ADDR config) {
    KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_AIV_ONLY);
    RshConfig c=LoadConfig(config);
    GlobalTensor<float>src,dst;GlobalTensor<int32_t>mapping;
    src.SetGlobalBuffer((__gm__ float*)packed);dst.SetGlobalBuffer((__gm__ float*)output);
    mapping.SetGlobalBuffer((__gm__ int32_t*)map);
    TPipe pipe;TBuf<TPosition::VECCALC>buffer;pipe.InitBuffer(buffer,256*sizeof(float));
    auto tmp=buffer.Get<float>();
    for(int32_t slot=GetBlockIdx();slot<c.groups*16;slot+=c.cores*2) {
        int32_t row=mapping.GetValue(slot);if(row<0)continue;
        DataCopy(tmp,src[(int64_t)slot*c.stride],c.stride);PipeBarrier<PIPE_ALL>();
        DataCopy(dst[(int64_t)row*c.stride],tmp,c.stride);PipeBarrier<PIPE_ALL>();
    }
}

extern "C" void rsh_launch_restore(void* stream,int blocks,void* packed,void* map,void* output,void* config) {
 rsh_restore<<<blocks,nullptr,stream>>>((GM_ADDR)packed,(GM_ADDR)map,(GM_ADDR)output,(GM_ADDR)config);
}
