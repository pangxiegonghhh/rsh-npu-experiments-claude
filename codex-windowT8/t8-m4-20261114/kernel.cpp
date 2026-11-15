#include "kernel_operator.h"
using namespace AscendC;
template<HardEvent E> __aicore__ inline void F(){SetFlag<E>(0);WaitFlag<E>(0);}
struct P4{uint32_t n,u,g,serial,windows,blocks,capture,commands;};
template<class T> __aicore__ inline uint32_t Fetch4(GlobalTensor<T>&src,GlobalTensor<uint32_t>&cmd,GlobalTensor<uint32_t>&offset,GlobalTensor<uint32_t>&bases,LocalTensor<T>&banks,const P4&x,uint32_t linear,uint32_t bank,uint32_t index){
 uint32_t tile=linear%(x.u/16),window=linear/(x.u/16)*x.blocks+GetBlockIdx(),base=bases.GetValue(window),count=0;
 auto dst=banks[(bank*x.g+index)*16*x.n];uint32_t first=offset.GetValue(tile),end=offset.GetValue(tile+1);
 for(uint32_t c=first;c<end;c++){
  uint32_t row=cmd.GetValue(c*8),h=cmd.GetValue(c*8+1),s=cmd.GetValue(c*8+2),stride=cmd.GetValue(c*8+3),k=cmd.GetValue(c*8+4);
  Nd2NzParams p{};p.ndNum=s;p.nValue=h;p.dValue=x.n;p.srcNdMatrixStride=s>1?stride*x.n:0;p.srcDValue=x.n;p.dstNzC0Stride=16;p.dstNzNStride=1;p.dstNzMatrixStride=h*(32/sizeof(T));
  DataCopy(dst[k*(32/sizeof(T))],src[uint64_t(base+row)*x.n],p);count++;
  if(x.serial)F<HardEvent::MTE2_S>();
 }
 return count;
}
template<class T> __aicore__ inline void Compute4(LocalTensor<T>&bl,TQue<TPosition::B2,2>&bqueue,LocalTensor<T>&aa,LocalTensor<float>&acc,GlobalTensor<float>&out,const P4&x,uint32_t linear){
 uint32_t slot=linear%2,tile=linear%(x.u/16),window=linear/(x.u/16)*x.blocks+GetBlockIdx();
 
 auto bb=bqueue.AllocTensor<T>();
 if constexpr(sizeof(T)==4){LoadData2dTransposeParams p{};p.repeatTimes=x.n/16;p.srcStride=1;p.dstGap=0;p.dstFracGap=x.n/16-1;LoadDataWithTranspose(bb,bl,p);}
 else{LoadData2DParams p{};p.repeatTimes=x.n/16;p.srcStride=1;p.ifTranspose=true;LoadData(bb,bl,p);}
 bqueue.EnQue(bb);bb=bqueue.DeQue<T>();MmadParams mm{};mm.m=16;mm.n=x.n;mm.k=16;mm.cmatrixInitVal=tile==0;
 if(tile==0)Mmad(acc,aa,bb,mm);else Mmad(acc,aa,bb,acc,mm);PipeBarrier<PIPE_M>();
 bqueue.FreeTensor(bb);
 if(x.capture&&tile+1==x.u/16){F<HardEvent::M_FIX>();FixpipeParamsV220 fp{};fp.ndNum=1;fp.mSize=16;fp.nSize=x.n;fp.srcStride=16;fp.dstStride=x.n;Fixpipe(out[uint64_t(window)*16*x.n],acc,fp);F<HardEvent::FIX_M>();}
}
template<class T> __aicore__ inline void Run4(GM_ADDR input,GM_ADDR commands,GM_ADDR offsets,GM_ADDR baseRows,GM_ADDR a,GM_ADDR output,GM_ADDR stats,const P4&x){
 TPipe pipe;TBuf<TPosition::B1>storage;TQue<TPosition::B2,2>b2;TBuf<TPosition::A2>a2;
 pipe.InitBuffer(storage,2*x.g*16*x.n*sizeof(T));pipe.InitBuffer(b2,2,16*x.n*sizeof(T));pipe.InitBuffer(a2,256*sizeof(T));auto banks=storage.Get<T>();auto aa=a2.Get<T>();LocalTensor<float>acc(TPosition::CO1,0,16*x.n);
 GlobalTensor<T>src,ag;src.SetGlobalBuffer((__gm__ T*)input);ag.SetGlobalBuffer((__gm__ T*)a);GlobalTensor<uint32_t>cmd,off,bases;cmd.SetGlobalBuffer((__gm__ uint32_t*)commands);off.SetGlobalBuffer((__gm__ uint32_t*)offsets);bases.SetGlobalBuffer((__gm__ uint32_t*)baseRows);GlobalTensor<float>out;out.SetGlobalBuffer((__gm__ float*)output);
 LoadData2DParams ap{};ap.repeatTimes=sizeof(T)==4?2:1;ap.srcStride=1;LoadData(aa,ag,ap);F<HardEvent::MTE2_M>();F<HardEvent::MTE2_S>();
 if constexpr(sizeof(T)==4)SetHF32Mode(HF32Mode::DISABLE);
 uint32_t total=x.windows*(x.u/16),calls=0;uint64_t begin=GetSystemCycle();
 if(x.serial){
  for(uint32_t t=0;t<total;t++){F<HardEvent::M_MTE2>();calls+=Fetch4(src,cmd,off,bases,banks,x,t,0,0);F<HardEvent::MTE2_MTE1>();auto bl=banks[0];Compute4(bl,b2,aa,acc,out,x,t);}
 }else{
  uint32_t first=total<x.g?total:x.g;for(uint32_t i=0;i<first;i++)calls+=Fetch4(src,cmd,off,bases,banks,x,i,0,i);SetFlag<HardEvent::MTE2_MTE1>(0);
  uint32_t batches=(total+x.g-1)/x.g;
  for(uint32_t p=0;p<batches;p++){
   uint32_t bank=p%2,next=1-bank,start=p*x.g,active=total-start<x.g?total-start:x.g,nextStart=start+x.g,nextActive=nextStart<total?(total-nextStart<x.g?total-nextStart:x.g):0;
   WaitFlag<HardEvent::MTE2_MTE1>(bank);if(nextActive&&p>=1)WaitFlag<HardEvent::MTE1_MTE2>(next);
   for(uint32_t i=0;i<active;i++){
    if(i<nextActive){calls+=Fetch4(src,cmd,off,bases,banks,x,nextStart+i,next,i);if(i+1==nextActive)SetFlag<HardEvent::MTE2_MTE1>(next);}
    auto bl=banks[(bank*x.g+i)*16*x.n];Compute4(bl,b2,aa,acc,out,x,start+i);
   }
   SetFlag<HardEvent::MTE1_MTE2>(bank);
  }
  for(uint32_t b=0;b<(batches>1?2:1);b++)WaitFlag<HardEvent::MTE1_MTE2>(b);
 }
 
 F<HardEvent::M_S>();F<HardEvent::MTE2_S>();if(x.capture)F<HardEvent::FIX_S>();uint64_t end=GetSystemCycle();
 GlobalTensor<uint32_t>st;st.SetGlobalBuffer((__gm__ uint32_t*)stats);uint32_t ix=GetBlockIdx()*32;st.SetValue(ix,uint32_t(begin));st.SetValue(ix+1,uint32_t(begin>>32));st.SetValue(ix+2,uint32_t(end));st.SetValue(ix+3,uint32_t(end>>32));st.SetValue(ix+4,calls);st.SetValue(ix+5,total);DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(st);
 if(!x.capture){F<HardEvent::M_FIX>();FixpipeParamsV220 fp{};fp.ndNum=1;fp.mSize=16;fp.nSize=x.n;fp.srcStride=16;fp.dstStride=x.n;Fixpipe(out[uint64_t(GetBlockIdx())*16*x.n],acc,fp);F<HardEvent::FIX_S>();}
}
extern "C" __global__ __aicore__ void m4_kernel(GM_ADDR in,GM_ADDR config,GM_ADDR commands,GM_ADDR offsets,GM_ADDR bases,GM_ADDR a,GM_ADDR out,GM_ADDR stats){
 KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_MIX_AIC_1_2);
 if ASCEND_IS_AIV {CrossCoreSetFlag<2,PIPE_MTE3>(7);}
 if ASCEND_IS_AIC {GlobalTensor<uint32_t>c;c.SetGlobalBuffer((__gm__ uint32_t*)config);P4 x{c.GetValue(1),c.GetValue(2),c.GetValue(3),c.GetValue(4),c.GetValue(5),c.GetValue(6),c.GetValue(7),c.GetValue(8)};if(c.GetValue(0))Run4<float>(in,commands,offsets,bases,a,out,stats,x);else Run4<half>(in,commands,offsets,bases,a,out,stats,x);CrossCoreWaitFlag<2,PIPE_MTE3>(7);}
 PipeBarrier<PIPE_ALL>();
}
extern "C" void t8_launch(void*s,void*i,void*c,void*cmd,void*off,void*bases,void*a,void*o,void*t,uint32_t blocks){m4_kernel<<<blocks,nullptr,s>>>((GM_ADDR)i,(GM_ADDR)c,(GM_ADDR)cmd,(GM_ADDR)off,(GM_ADDR)bases,(GM_ADDR)a,(GM_ADDR)o,(GM_ADDR)t);}
