#include "kernel_operator.h"
using namespace AscendC;
template<HardEvent E> __aicore__ inline void F(){SetFlag<E>(0);WaitFlag<E>(0);}
struct P{uint32_t n,tiles,g,serial,cycles,blocks,capture,path,windows,zeroRow,aMode,mode,batch,active;};
template<class T> __aicore__ inline void LoadB(LocalTensor<T>&bb,LocalTensor<T>&bl,uint32_t n){
 if constexpr(sizeof(T)==4){LoadData2dTransposeParams p{};p.repeatTimes=n/16;p.srcStride=1;p.dstFracGap=n/16-1;LoadDataWithTranspose(bb,bl,p);}
 else{LoadData2DParams p{};p.repeatTimes=n/16;p.srcStride=1;p.ifTranspose=true;LoadData(bb,bl,p);}
}
template<class T> __aicore__ inline void LoadA(LocalTensor<T>&aa,LocalTensor<T>&al,GlobalTensor<T>&ag,uint32_t mode){
 if(mode==0){LoadData2DParams p{};p.repeatTimes=sizeof(T)==4?2:1;p.srcStride=1;LoadData(aa,ag,p);F<HardEvent::MTE2_M>();return;}
 if(mode==1){Nd2NzParams p{};p.ndNum=1;p.nValue=16;p.dValue=16;p.srcDValue=16;p.dstNzC0Stride=16;p.dstNzNStride=1;DataCopy(al,ag,p);}
 else{
  if constexpr(sizeof(T)==2)DataCopy(al,ag,256);
  else{DataCopyParams p{};p.blockCount=16;p.blockLen=1;p.srcStride=1;p.dstStride=0;DataCopy(al,ag,p);DataCopy(al[128],ag[8],p);}
 }
 F<HardEvent::MTE2_MTE1>();LoadData2dTransposeParams p{};p.repeatTimes=1;p.srcStride=1;if constexpr(sizeof(T)==4)p.dstGap=1;LoadDataWithTranspose(aa,al,p);F<HardEvent::MTE1_M>();
}
template<class T> __aicore__ inline uint32_t Fetch(GlobalTensor<T>&src,GlobalTensor<uint32_t>&cmd,GlobalTensor<uint32_t>&off,GlobalTensor<uint32_t>&bases,GlobalTensor<uint32_t>&cfg,LocalTensor<T>&banks,const P&x,uint32_t linear,uint32_t bank,uint32_t index){
 uint32_t ti=linear%x.tiles,epoch=linear/x.tiles,base=bases.GetValue(epoch*x.blocks+GetBlockIdx()),count=0,c0=32/sizeof(T);
 auto dst=banks[(bank*x.g+index)*16*x.n];
 if(x.path==0){
  for(uint32_t i=off.GetValue(ti);i<off.GetValue(ti+1);i++){
   uint32_t row=cmd.GetValue(i*8),h=cmd.GetValue(i*8+1),s=cmd.GetValue(i*8+2),stride=cmd.GetValue(i*8+3),k=cmd.GetValue(i*8+4);
   // Zero tail rows are fixed per source replica and never read outside B allocation.
   Nd2NzParams p{};p.ndNum=s;p.nValue=h;p.dValue=x.n;p.srcNdMatrixStride=s>1?stride*x.n:0;p.srcDValue=x.n;p.dstNzC0Stride=16;p.dstNzNStride=1;p.dstNzMatrixStride=h*c0;
   DataCopy(dst[k*c0],src[uint64_t(row>=x.zeroRow?cfg.GetValue(21)+row-x.zeroRow-16:base+row)*x.n],p);count++;
  }
 }else if(x.path==1){
  DataCopyParams p{};p.blockCount=x.n/c0;p.blockLen=1;p.srcStride=0;p.dstStride=15;
  for(uint32_t k=0;k<16;k++){uint32_t row=cfg.GetValue(24+x.tiles*3+ti*16+k);DataCopy(dst[k*c0],src[uint64_t(row>=x.zeroRow?cfg.GetValue(21)+row-x.zeroRow-16:base+row)*x.n],p);count++;}
 }else{
  uint32_t k=0;
  while(k<16){uint32_t row=cfg.GetValue(24+x.tiles*3+ti*16+k),h=1;while(k+h<16&&cfg.GetValue(24+x.tiles*3+ti*16+k+h)==row+h)h++;
   DataCopyParams p{};p.blockCount=h;p.blockLen=1;p.srcStride=x.n/c0-1;p.dstStride=0;
   for(uint32_t j=0;j<x.n/c0;j++){DataCopy(dst[j*16*c0+k*c0],src[uint64_t(row>=x.zeroRow?cfg.GetValue(21)+row-x.zeroRow-16:base+row)*x.n+j*c0],p);count++;}k+=h;
  }
 }
 return count;
}
template<class T> __aicore__ inline void Compute(LocalTensor<T>&bl,TQue<TPosition::B2,2>&bq,LocalTensor<T>&aa,LocalTensor<float>&acc,GlobalTensor<float>&out,GlobalTensor<uint32_t>&cfg,const P&x,uint32_t linear){
 uint32_t ti=linear%x.tiles,epoch=linear/x.tiles,window=cfg.GetValue(24+ti*3),tile=cfg.GetValue(24+ti*3+1),last=cfg.GetValue(24+ti*3+2);
 auto bb=bq.AllocTensor<T>();LoadB(bb,bl,x.n);bq.EnQue(bb);bb=bq.DeQue<T>();
 MmadParams mm{};mm.m=16;mm.n=x.n;mm.k=16;mm.cmatrixInitVal=tile==0;
 if(tile==0)Mmad(acc,aa,bb,mm);else Mmad(acc,aa,bb,acc,mm);PipeBarrier<PIPE_M>();bq.FreeTensor(bb);
 if(x.capture&&last){F<HardEvent::M_FIX>();FixpipeParamsV220 fp{};fp.ndNum=1;fp.mSize=16;fp.nSize=x.n;fp.srcStride=16;fp.dstStride=x.n;Fixpipe(out[(uint64_t(epoch*x.windows+window)*x.blocks+GetBlockIdx())*16*x.n],acc,fp);F<HardEvent::FIX_M>();}
}
template<class T> __aicore__ inline void Run(GM_ADDR input,GM_ADDR config,GM_ADDR commands,GM_ADDR offsets,GM_ADDR baseRows,GM_ADDR a,GM_ADDR output,GM_ADDR stats,const P&x){
 TPipe pipe;TBuf<TPosition::B1>storage;TQue<TPosition::B2,2>bq;TBuf<TPosition::A2>a2;TBuf<TPosition::A1>a1;
 pipe.InitBuffer(storage,2*x.g*16*x.n*sizeof(T));pipe.InitBuffer(bq,2,16*x.n*sizeof(T));pipe.InitBuffer(a2,256*sizeof(T));pipe.InitBuffer(a1,256*sizeof(T));
 auto banks=storage.Get<T>(),aa=a2.Get<T>(),al=a1.Get<T>();LocalTensor<float>acc(TPosition::CO1,0,16*x.n);
 GlobalTensor<T>src,ag;src.SetGlobalBuffer((__gm__ T*)input);ag.SetGlobalBuffer((__gm__ T*)a);
 GlobalTensor<uint32_t>cmd,off,bases,cfg;cmd.SetGlobalBuffer((__gm__ uint32_t*)commands);off.SetGlobalBuffer((__gm__ uint32_t*)offsets);bases.SetGlobalBuffer((__gm__ uint32_t*)baseRows);cfg.SetGlobalBuffer((__gm__ uint32_t*)config);
 GlobalTensor<float>out;out.SetGlobalBuffer((__gm__ float*)output);
 LoadA(aa,al,ag,x.aMode);F<HardEvent::MTE2_S>();if constexpr(sizeof(T)==4)SetHF32Mode(HF32Mode::DISABLE);
 uint32_t total=x.cycles*x.tiles,calls=0;uint64_t begin,end;
 if(x.mode){
  Fetch(src,cmd,off,bases,cfg,banks,x,0,0,0);F<HardEvent::MTE2_MTE1>();auto bl=banks[0];auto bb=bq.AllocTensor<T>();
  begin=GetSystemCycle();
  for(uint32_t b=0;b<x.batch;b++){
   if(x.mode==1){
    uint32_t c0=32/sizeof(T),h=x.active;
    if(x.path==0){Nd2NzParams p{};p.ndNum=1;p.nValue=h;p.dValue=x.n;p.srcDValue=x.n;p.dstNzC0Stride=16;p.dstNzNStride=1;DataCopy(bl,src,p);calls++;}
    else if(x.path==1){DataCopyParams p{};p.blockCount=x.n/c0;p.blockLen=1;p.dstStride=15;for(uint32_t k=0;k<h;k++){DataCopy(bl[k*c0],src[k*x.n],p);calls++;}}
    else{DataCopyParams p{};p.blockCount=h;p.blockLen=1;p.srcStride=x.n/c0-1;for(uint32_t j=0;j<x.n/c0;j++){DataCopy(bl[j*16*c0],src[j*c0],p);calls++;}}
    F<HardEvent::MTE2_S>();
   }else if(x.mode==2){LoadB(bb,bl,x.n);F<HardEvent::MTE1_M>();F<HardEvent::M_S>();calls++;}
   else if(x.mode==3){LoadData2DParams p{};p.repeatTimes=16*x.n*sizeof(T)/512;p.srcStride=1;LoadData(bb,bl,p);F<HardEvent::MTE1_M>();F<HardEvent::M_S>();calls++;}
   else{LoadA(aa,al,ag,x.aMode);F<HardEvent::MTE2_S>();F<HardEvent::MTE1_M>();F<HardEvent::M_S>();calls++;}
  }
  end=GetSystemCycle();bq.FreeTensor(bb);
  // Microbench readback checks the final logical chain; plain-load primitive has separate semantics.
  F<HardEvent::MTE2_MTE1>();Compute(bl,bq,aa,acc,out,cfg,x,0);total=x.batch;
 }else{
  begin=GetSystemCycle();
  if(x.serial){for(uint32_t t=0;t<total;t++){F<HardEvent::M_MTE2>();calls+=Fetch(src,cmd,off,bases,cfg,banks,x,t,0,0);F<HardEvent::MTE2_MTE1>();auto bl=banks[0];Compute(bl,bq,aa,acc,out,cfg,x,t);}}
  else{
   uint32_t first=total<x.g?total:x.g;for(uint32_t i=0;i<first;i++)calls+=Fetch(src,cmd,off,bases,cfg,banks,x,i,0,i);SetFlag<HardEvent::MTE2_MTE1>(0);
   uint32_t batches=(total+x.g-1)/x.g;
   for(uint32_t p=0;p<batches;p++){
    uint32_t bank=p%2,next=1-bank,start=p*x.g,active=total-start<x.g?total-start:x.g,nextStart=start+x.g,nextActive=nextStart<total?(total-nextStart<x.g?total-nextStart:x.g):0;
    WaitFlag<HardEvent::MTE2_MTE1>(bank);if(nextActive&&p>=1)WaitFlag<HardEvent::MTE1_MTE2>(next);
    for(uint32_t i=0;i<active;i++){
     if(i<nextActive){calls+=Fetch(src,cmd,off,bases,cfg,banks,x,nextStart+i,next,i);if(i+1==nextActive)SetFlag<HardEvent::MTE2_MTE1>(next);}
     auto bl=banks[(bank*x.g+i)*16*x.n];Compute(bl,bq,aa,acc,out,cfg,x,start+i);
    }SetFlag<HardEvent::MTE1_MTE2>(bank);
   }for(uint32_t b=0;b<(batches>1?2:1);b++)WaitFlag<HardEvent::MTE1_MTE2>(b);
  }
  F<HardEvent::M_S>();F<HardEvent::MTE2_S>();if(x.capture)F<HardEvent::FIX_S>();end=GetSystemCycle();
 }
 GlobalTensor<uint32_t>st;st.SetGlobalBuffer((__gm__ uint32_t*)stats);uint32_t ix=GetBlockIdx()*32;st.SetValue(ix,uint32_t(begin));st.SetValue(ix+1,uint32_t(begin>>32));st.SetValue(ix+2,uint32_t(end));st.SetValue(ix+3,uint32_t(end>>32));st.SetValue(ix+4,calls);st.SetValue(ix+5,total);DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(st);
 if(!x.capture){F<HardEvent::M_FIX>();FixpipeParamsV220 fp{};fp.ndNum=1;fp.mSize=16;fp.nSize=x.n;fp.srcStride=16;fp.dstStride=x.n;Fixpipe(out[uint64_t(GetBlockIdx())*16*x.n],acc,fp);F<HardEvent::FIX_S>();}
}
extern "C" __global__ __aicore__ void m11_kernel(GM_ADDR in,GM_ADDR config,GM_ADDR commands,GM_ADDR offsets,GM_ADDR bases,GM_ADDR a,GM_ADDR out,GM_ADDR stats){
 KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_MIX_AIC_1_2);
 if ASCEND_IS_AIV {CrossCoreSetFlag<2,PIPE_MTE3>(7);}
 if ASCEND_IS_AIC {GlobalTensor<uint32_t>c;c.SetGlobalBuffer((__gm__ uint32_t*)config);P x{c.GetValue(1),c.GetValue(2),c.GetValue(3),c.GetValue(4),c.GetValue(5),c.GetValue(6),c.GetValue(7),c.GetValue(8),c.GetValue(9),c.GetValue(10),c.GetValue(13),c.GetValue(14),c.GetValue(15),c.GetValue(20)};if(c.GetValue(0))Run<float>(in,config,commands,offsets,bases,a,out,stats,x);else Run<half>(in,config,commands,offsets,bases,a,out,stats,x);CrossCoreWaitFlag<2,PIPE_MTE3>(7);}
 PipeBarrier<PIPE_ALL>();
}
extern "C" void t8_launch(void*s,void*i,void*c,void*cmd,void*off,void*bases,void*a,void*o,void*t,uint32_t blocks){m11_kernel<<<blocks,nullptr,s>>>((GM_ADDR)i,(GM_ADDR)c,(GM_ADDR)cmd,(GM_ADDR)off,(GM_ADDR)bases,(GM_ADDR)a,(GM_ADDR)o,(GM_ADDR)t);}
