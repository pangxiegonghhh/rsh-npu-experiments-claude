#include "kernel_operator.h"
using namespace AscendC;
template<HardEvent E> __aicore__ inline void F(){SetFlag<E>(0);WaitFlag<E>(0);}
template<class T> __aicore__ inline void CopyM5(LocalTensor<T>& dst,GlobalTensor<T>& src,uint32_t kind,uint32_t split,uint32_t segments,uint32_t rows,uint32_t gap,uint32_t n){
 const uint32_t c0=32/sizeof(T),kp=((segments*rows+15)/16)*16;
 if(kind==0){DataCopyParams p{};p.blockCount=split?1:segments;p.blockLen=rows*n*sizeof(T)/32;p.srcStride=split?0:gap*n*sizeof(T)/32;
  if(split){for(uint32_t s=0;s<segments;s++)DataCopy(dst[s*rows*n],src[uint64_t(s)*(rows+gap)*n],p);}
  else DataCopy(dst,src,p);
 }else{Nd2NzParams p{};p.ndNum=split?1:segments;p.nValue=rows;p.dValue=n;p.srcNdMatrixStride=(rows+gap)*n;p.srcDValue=n;p.dstNzC0Stride=kp;p.dstNzNStride=1;p.dstNzMatrixStride=rows*c0;
  if(split){for(uint32_t s=0;s<segments;s++)DataCopy(dst[s*rows*c0],src[uint64_t(s)*(rows+gap)*n],p);}
  else DataCopy(dst,src,p);
 }
}
extern "C" __global__ __aicore__ void m5_kernel(GM_ADDR input,GM_ADDR init,GM_ADDR eye,GM_ADDR output,GM_ADDR stats,uint32_t dtype,uint32_t kind,uint32_t split,uint32_t segments,uint32_t rows,uint32_t gap,uint32_t n,uint32_t rounds,uint32_t bytes){
 KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_MIX_AIC_1_2);
 if ASCEND_IS_AIV {CrossCoreSetFlag<2,PIPE_MTE3>(7);}
 if ASCEND_IS_AIC {
  TPipe pipe;TBuf<TPosition::B1> b1;TBuf<TPosition::B2>b2;TBuf<TPosition::A2>a2;pipe.InitBuffer(b1,bytes);pipe.InitBuffer(b2,512);pipe.InitBuffer(a2,512);
  auto all=b1.Get<half>();auto bh=b2.Get<half>();auto ah=a2.Get<half>();LocalTensor<float> acc(TPosition::CO1,0,256);
  GlobalTensor<half> seed,identity;seed.SetGlobalBuffer((__gm__ half*)init);identity.SetGlobalBuffer((__gm__ half*)eye);DataCopy(all,seed,bytes/2);F<HardEvent::MTE2_S>();
  uint64_t begin=GetSystemCycle();
  if(dtype==0){auto dst=all[256];GlobalTensor<half>src;src.SetGlobalBuffer((__gm__ half*)input);for(uint32_t i=0;i<rounds;i++)CopyM5(dst,src,kind,split,segments,rows,gap,n);}
  else{auto whole=b1.Get<float>();auto dst=whole[128];GlobalTensor<float>src;src.SetGlobalBuffer((__gm__ float*)input);for(uint32_t i=0;i<rounds;i++)CopyM5(dst,src,kind,split,segments,rows,gap,n);}
  F<HardEvent::MTE2_S>();uint64_t end=GetSystemCycle();
  GlobalTensor<uint32_t> st;st.SetGlobalBuffer((__gm__ uint32_t*)stats);st.SetValue(0,uint32_t(begin));st.SetValue(1,uint32_t(begin>>32));st.SetValue(2,uint32_t(end));st.SetValue(3,uint32_t(end>>32));st.SetValue(4,rounds*(split?segments:1));DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(st);
  LoadData2DParams ap{};ap.repeatTimes=1;ap.srcStride=1;LoadData(ah,identity,ap);F<HardEvent::MTE2_M>();GlobalTensor<float>out;out.SetGlobalBuffer((__gm__ float*)output);
  for(uint32_t ch=0;ch<bytes/512;ch++){F<HardEvent::M_MTE1>();LoadData2DParams bp{};bp.repeatTimes=1;bp.srcStride=1;bp.ifTranspose=true;LoadData(bh,all[ch*256],bp);F<HardEvent::MTE1_M>();MmadParams mm{};mm.m=16;mm.n=16;mm.k=16;mm.cmatrixInitVal=true;Mmad(acc,ah,bh,mm);F<HardEvent::M_FIX>();FixpipeParamsV220 fp{};fp.ndNum=1;fp.mSize=16;fp.nSize=16;fp.srcStride=16;fp.dstStride=16;Fixpipe(out[ch*256],acc,fp);F<HardEvent::FIX_M>();F<HardEvent::FIX_S>();}
  CrossCoreWaitFlag<2,PIPE_MTE3>(7);
 }
 PipeBarrier<PIPE_ALL>();
}
extern "C" void t8_launch(void*s,void*i,void*z,void*e,void*o,void*t,uint32_t dtype,uint32_t kind,uint32_t split,uint32_t seg,uint32_t rows,uint32_t gap,uint32_t n,uint32_t rounds,uint32_t bytes){m5_kernel<<<1,nullptr,s>>>((GM_ADDR)i,(GM_ADDR)z,(GM_ADDR)e,(GM_ADDR)o,(GM_ADDR)t,dtype,kind,split,seg,rows,gap,n,rounds,bytes);}
