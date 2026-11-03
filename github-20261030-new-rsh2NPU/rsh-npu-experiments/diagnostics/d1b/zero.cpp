#include "kernel_operator.h"
using namespace AscendC;
extern "C" __global__ __aicore__ void rsh_zero(GM_ADDR output,uint64_t count) {
    KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_AIV_ONLY);
    constexpr uint32_t tile=8192;
    TPipe pipe;TBuf<TPosition::VECCALC> buffer;
    pipe.InitBuffer(buffer,tile*sizeof(float));
    GlobalTensor<float> out;out.SetGlobalBuffer((__gm__ float*)output);
    auto zeros=buffer.Get<float>();Duplicate(zeros,0.0f,tile);PipeBarrier<PIPE_ALL>();
    for(uint64_t offset=(uint64_t)GetBlockIdx()*tile;offset<count;offset+=(uint64_t)GetBlockNum()*tile){
        uint32_t size=(count-offset<tile)?(uint32_t)(count-offset):tile;
        // Actual output buffers have a multiple of 16 floats, hence every copy is 32-byte aligned.
        DataCopy(out[offset],zeros,size);PipeBarrier<PIPE_ALL>();
    }
}
extern "C" void rsh_launch_zero(void* stream,int blocks,void* output,uint64_t count){
    rsh_zero<<<blocks,nullptr,stream>>>((GM_ADDR)output,count);
}
