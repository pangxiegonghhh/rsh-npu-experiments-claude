#include "kernel_operator.h"
using namespace AscendC;
template<HardEvent E> __aicore__ inline void F(){SetFlag<E>(0);WaitFlag<E>(0);}
struct X{uint32_t n,path,capture,rounds,blocks,tiles,windows,maxTiles,zero;};
__aicore__ inline void Write64(GlobalTensor<uint32_t>&s,uint32_t p,uint64_t v){s.SetValue(p,uint32_t(v));s.SetValue(p+1,uint32_t(v>>32));}
template<class T> __aicore__ inline void Pack(GM_ADDR input,GM_ADDR rows,GM_ADDR windows,GM_ADDR bases,GM_ADDR ring,GM_ADDR stats,const X&x){
 const uint32_t sub=GetSubBlockIdx(),group=GetBlockIdx()/2;TPipe pipe;TBuf<TPosition::VECCALC>buf;pipe.InitBuffer(buf,16*x.n*sizeof(T));auto ub=buf.Get<T>();
 GlobalTensor<T>src,dst;src.SetGlobalBuffer((__gm__ T*)input);dst.SetGlobalBuffer((__gm__ T*)ring);
 GlobalTensor<uint32_t>rr,ww,bb,st;rr.SetGlobalBuffer((__gm__ uint32_t*)rows);ww.SetGlobalBuffer((__gm__ uint32_t*)windows);bb.SetGlobalBuffer((__gm__ uint32_t*)bases);st.SetGlobalBuffer((__gm__ uint32_t*)stats);
 uint64_t total=0,begin=GetSystemCycle();uint32_t calls=0;
 for(uint32_t i=0;i<x.rounds;i++){
  if(i)CrossCoreWaitFlag<2,PIPE_M>(2);
  if(sub==0){uint32_t w=i*x.blocks+group,wi=w%x.windows,first=ww.GetValue(wi*4),count=ww.GetValue(wi*4+1),base=bb.GetValue(w);uint64_t start=GetSystemCycle();
   for(uint32_t t=0;t<count;t++){
    for(uint32_t k=0;k<16;k++){uint32_t row=rr.GetValue((first+t)*16+k);DataCopy(ub[k*x.n],src[uint64_t(row==0xffffffff?x.zero:base+row)*x.n],x.n);calls++;}
    F<HardEvent::MTE2_MTE3>();DataCopy(dst[(uint64_t(group)*x.maxTiles+t)*16*x.n],ub,16*x.n);F<HardEvent::MTE3_MTE2>();
   }F<HardEvent::MTE3_S>();total+=GetSystemCycle()-start;
  }
  PipeBarrier<PIPE_ALL>();CrossCoreSetFlag<2,PIPE_MTE3>(0);
 }
 CrossCoreWaitFlag<2,PIPE_M>(2);uint64_t end=GetSystemCycle();
 if(sub==0){uint32_t p=(x.blocks+group)*32;Write64(st,p,begin);Write64(st,p+2,end);Write64(st,p+4,total);st.SetValue(p+6,calls);DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(st);}
 PipeBarrier<PIPE_ALL>();CrossCoreSetFlag<2,PIPE_MTE3>(7);
}
template<class T> __aicore__ inline void ReadTile(GlobalTensor<T>&src,GlobalTensor<T>&ring,GlobalTensor<uint32_t>&cmd,GlobalTensor<uint32_t>&off,LocalTensor<T>&banks,const X&x,uint32_t first,uint32_t tile,uint32_t base,uint32_t bank){
 auto dst=banks[bank*16*x.n];
 if(x.path==2){Nd2NzParams p{};p.ndNum=1;p.nValue=16;p.dValue=x.n;p.srcDValue=x.n;p.dstNzC0Stride=16;p.dstNzNStride=1;p.dstNzMatrixStride=16;DataCopy(dst,ring[(uint64_t(GetBlockIdx())*x.maxTiles+tile)*16*x.n],p);}
 else for(uint32_t c=off.GetValue(first+tile);c<off.GetValue(first+tile+1);c++){
  uint32_t row=cmd.GetValue(c*8),h=cmd.GetValue(c*8+1),s=cmd.GetValue(c*8+2),stride=cmd.GetValue(c*8+3),k=cmd.GetValue(c*8+4);
  Nd2NzParams p{};p.ndNum=s;p.nValue=h;p.dValue=x.n;p.srcNdMatrixStride=s>1?stride*x.n:0;p.srcDValue=x.n;p.dstNzC0Stride=16;p.dstNzNStride=1;p.dstNzMatrixStride=h*(32/sizeof(T));
  DataCopy(dst[k*(32/sizeof(T))],src[uint64_t(row==0xffffffff?x.zero:base+row)*x.n],p);
 }
}
template<class T> __aicore__ inline void Consume(LocalTensor<T>&bl,TQue<TPosition::B2,2>&bq,LocalTensor<T>&aa,LocalTensor<float>&acc,GlobalTensor<float>&out,const X&x,uint32_t w,uint32_t tile){
 auto b=bq.AllocTensor<T>();
 if constexpr(sizeof(T)==4){LoadData2dTransposeParams p{};p.repeatTimes=x.n/16;p.srcStride=1;p.dstGap=0;p.dstFracGap=x.n/16-1;LoadDataWithTranspose(b,bl,p);}
 else{LoadData2DParams p{};p.repeatTimes=x.n/16;p.srcStride=1;p.ifTranspose=true;LoadData(b,bl,p);}
 bq.EnQue(b);b=bq.DeQue<T>();MmadParams mm{};mm.m=16;mm.n=x.n;mm.k=16;mm.cmatrixInitVal=true;Mmad(acc,aa,b,mm);PipeBarrier<PIPE_M>();bq.FreeTensor(b);
 if(x.capture){F<HardEvent::M_FIX>();FixpipeParamsV220 fp{};fp.ndNum=1;fp.mSize=16;fp.nSize=x.n;fp.srcStride=16;fp.dstStride=x.n;Fixpipe(out[(uint64_t(w)*x.maxTiles+tile)*16*x.n],acc,fp);F<HardEvent::FIX_M>();}
}
template<class T> __aicore__ inline void Reader(GM_ADDR input,GM_ADDR commands,GM_ADDR offsets,GM_ADDR windows,GM_ADDR bases,GM_ADDR a,GM_ADDR ring,GM_ADDR output,GM_ADDR stats,const X&x){
 TPipe pipe;TBuf<TPosition::B1>storage;TQue<TPosition::B2,2>bq;TBuf<TPosition::A2>a2;
 pipe.InitBuffer(storage,2*16*x.n*sizeof(T));pipe.InitBuffer(bq,2,16*x.n*sizeof(T));pipe.InitBuffer(a2,256*sizeof(T));auto banks=storage.Get<T>();auto aa=a2.Get<T>();LocalTensor<float>acc(TPosition::CO1,0,16*x.n);
 GlobalTensor<T>src,ag,rg;src.SetGlobalBuffer((__gm__ T*)input);ag.SetGlobalBuffer((__gm__ T*)a);rg.SetGlobalBuffer((__gm__ T*)ring);
 GlobalTensor<uint32_t>cmd,off,ww,bb,st;cmd.SetGlobalBuffer((__gm__ uint32_t*)commands);off.SetGlobalBuffer((__gm__ uint32_t*)offsets);ww.SetGlobalBuffer((__gm__ uint32_t*)windows);bb.SetGlobalBuffer((__gm__ uint32_t*)bases);st.SetGlobalBuffer((__gm__ uint32_t*)stats);GlobalTensor<float>out;out.SetGlobalBuffer((__gm__ float*)output);
 LoadData2DParams ap{};ap.repeatTimes=sizeof(T)==4?2:1;ap.srcStride=1;LoadData(aa,ag,ap);F<HardEvent::MTE2_M>();F<HardEvent::MTE2_S>();if constexpr(sizeof(T)==4)SetHF32Mode(HF32Mode::DISABLE);
 uint64_t begin=GetSystemCycle(),total=0;uint32_t tiles=0;
 for(uint32_t i=0;i<x.rounds;i++){
  uint32_t w=i*x.blocks+GetBlockIdx(),wi=w%x.windows,first=ww.GetValue(wi*4),count=ww.GetValue(wi*4+1),base=bb.GetValue(w);if(x.path==2)CrossCoreWaitFlag<2,PIPE_MTE2>(0);uint64_t start=GetSystemCycle();
  ReadTile(src,rg,cmd,off,banks,x,first,0,base,0);SetFlag<HardEvent::MTE2_MTE1>(0);
  for(uint32_t t=0;t<count;t++){
   uint32_t bank=t%2,next=1-bank;WaitFlag<HardEvent::MTE2_MTE1>(bank);
   if(t+1<count){if(t)WaitFlag<HardEvent::MTE1_MTE2>(next);ReadTile(src,rg,cmd,off,banks,x,first,t+1,base,next);SetFlag<HardEvent::MTE2_MTE1>(next);}
   auto bl=banks[bank*16*x.n];Consume(bl,bq,aa,acc,out,x,w,t);SetFlag<HardEvent::MTE1_MTE2>(bank);
  }
  for(uint32_t b=0;b<(count>1?2u:1u);b++)WaitFlag<HardEvent::MTE1_MTE2>(b);
  F<HardEvent::M_MTE2>();F<HardEvent::M_S>();F<HardEvent::MTE2_S>();if(x.capture)F<HardEvent::FIX_S>();total+=GetSystemCycle()-start;tiles+=count;
  if(x.path==2){PipeBarrier<PIPE_ALL>();CrossCoreSetFlag<2,PIPE_M>(2);}
 }
 uint64_t end=GetSystemCycle();uint32_t p=GetBlockIdx()*32;Write64(st,p,begin);Write64(st,p+2,end);Write64(st,p+4,total);st.SetValue(p+6,tiles);DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(st);
 if(!x.capture){F<HardEvent::M_FIX>();FixpipeParamsV220 fp{};fp.ndNum=1;fp.mSize=16;fp.nSize=x.n;fp.srcStride=16;fp.dstStride=x.n;Fixpipe(out[uint64_t(GetBlockIdx())*16*x.n],acc,fp);F<HardEvent::FIX_S>();}
 CrossCoreWaitFlag<2,PIPE_MTE3>(7);
}
extern "C" __global__ __aicore__ void m8_kernel(GM_ADDR in,GM_ADDR config,GM_ADDR commands,GM_ADDR offsets,GM_ADDR rows,GM_ADDR windows,GM_ADDR bases,GM_ADDR a,GM_ADDR ring,GM_ADDR out,GM_ADDR stats){
 KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_MIX_AIC_1_2);GlobalTensor<uint32_t>c;c.SetGlobalBuffer((__gm__ uint32_t*)config);
 X x{c.GetValue(1),c.GetValue(2),c.GetValue(3),c.GetValue(4),c.GetValue(5),c.GetValue(6),c.GetValue(7),c.GetValue(8),c.GetValue(18)};
 if ASCEND_IS_AIV {if(x.path==2){if(c.GetValue(0))Pack<float>(in,rows,windows,bases,ring,stats,x);else Pack<half>(in,rows,windows,bases,ring,stats,x);}else CrossCoreSetFlag<2,PIPE_MTE3>(7);}
 if ASCEND_IS_AIC {if(c.GetValue(0))Reader<float>(in,commands,offsets,windows,bases,a,ring,out,stats,x);else Reader<half>(in,commands,offsets,windows,bases,a,ring,out,stats,x);}
 PipeBarrier<PIPE_ALL>();
}
extern "C" void t8_launch(void*s,void*i,void*c,void*cmd,void*off,void*rows,void*windows,void*bases,void*a,void*ring,void*o,void*t,uint32_t blocks){m8_kernel<<<blocks,nullptr,s>>>((GM_ADDR)i,(GM_ADDR)c,(GM_ADDR)cmd,(GM_ADDR)off,(GM_ADDR)rows,(GM_ADDR)windows,(GM_ADDR)bases,(GM_ADDR)a,(GM_ADDR)ring,(GM_ADDR)o,(GM_ADDR)t);}
