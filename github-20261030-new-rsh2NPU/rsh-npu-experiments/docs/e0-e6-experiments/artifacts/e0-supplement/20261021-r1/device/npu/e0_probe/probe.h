#pragma once
#include "kernel_operator.h"
using namespace AscendC;
// Configuration: logical M,K,N; physical Mp,Kp,Np; B layout, K16 loop,
// compact source width (0=dense), bulk load, logical dimensions flag.
template<bool Direct> class Probe {
 TPipe pipe;
 TQue<TPosition::A1,1> aq; TQue<TPosition::B1,1> bq;
 TQue<TPosition::A2,1> a2q; TQue<TPosition::B2,1> b2q;
 TQue<TPosition::CO1,1> cq;
 GlobalTensor<half> a,b; GlobalTensor<int32_t> refs,cf;
 GlobalTensor<float> out; GlobalTensor<int32_t> debug;
 int m,k,n,mp,kp,np,layout,split,compact,bulk,logical,bbulk;
public:
 __aicore__ inline void Run(GM_ADDR av,GM_ADDR bv,GM_ADDR rv,GM_ADDR ov,GM_ADDR cv,GM_ADDR dv){
  cf.SetGlobalBuffer((__gm__ int32_t*)cv);a.SetGlobalBuffer((__gm__ half*)av);
  b.SetGlobalBuffer((__gm__ half*)bv);refs.SetGlobalBuffer((__gm__ int32_t*)rv);
  out.SetGlobalBuffer((__gm__ float*)ov);debug.SetGlobalBuffer((__gm__ int32_t*)dv);
  m=cf.GetValue(0);k=cf.GetValue(1);n=cf.GetValue(2);
  mp=cf.GetValue(3);kp=cf.GetValue(4);np=cf.GetValue(5);
  layout=cf.GetValue(6);split=cf.GetValue(7);compact=cf.GetValue(8);
  bulk=cf.GetValue(9);logical=cf.GetValue(10);bbulk=cf.GetValue(11);
  int mb=mp/16,kb=kp/16,nb=np/16;
  event_t ready{},reuse{};
  if constexpr(Direct){ready=static_cast<event_t>(pipe.FetchEventID(HardEvent::MTE2_M));reuse=static_cast<event_t>(pipe.FetchEventID(HardEvent::M_MTE2));}
  pipe.InitBuffer(aq,1,mp*kp*2);pipe.InitBuffer(bq,1,kp*np*2);
  pipe.InitBuffer(a2q,1,mp*kp*2);pipe.InitBuffer(b2q,1,kp*np*2);
  pipe.InitBuffer(cq,1,mp*np*4);
  LocalTensor<half> al;
  if constexpr(!Direct){
   al=aq.AllocTensor<half>();Nd2NzParams nd{};
   nd.ndNum=1;nd.nValue=mp;nd.dValue=compact?compact:kp;
   nd.srcDValue=nd.dValue;nd.dstNzC0Stride=mp;nd.dstNzNStride=1;
   DataCopy(al,a,nd);aq.EnQue(al);al=aq.DeQue<half>();
  }
  auto bl=bq.AllocTensor<half>();
  for(int r=0;r<kp;++r){
   int k1=r/16,k0=r%16;int row=refs.GetValue(r);
   DataCopyParams cp{};cp.blockCount=nb;cp.blockLen=1;
   cp.dstStride=layout?15:kb*16-1;
   int off=layout?k1*nb*256+k0*16:k1*256+k0*16;
   DataCopy(bl[off],b[row*np],cp);
  }
  bq.EnQue(bl);bl=bq.DeQue<half>();
  auto acc=cq.AllocTensor<float>();int calls=0;
  for(int step=0;step<(split?kb:1);++step){
   auto aa=a2q.AllocTensor<half>();auto bb=b2q.AllocTensor<half>();
   int active=split?1:kb;
   if constexpr(Direct){SetFlag<HardEvent::M_MTE2>(reuse);WaitFlag<HardEvent::M_MTE2>(reuse);}
   for(int mi=0;mi<mb;++mi){
    for(int ki=0;ki<(bulk?1:active);++ki){
     LoadData2DParams ld{};ld.repeatTimes=bulk?active:1;
     ld.srcStride=Direct?1:mb;ld.ifTranspose=false;
     int srcK=split?step:ki;int dst=(mi*active+ki)*256;
     if constexpr(Direct) LoadData(aa[dst],a[(mi*kb+srcK)*256],ld);
     else LoadData(aa[dst],al[(srcK*mb+mi)*256],ld);
    }
   }
   for(int ki=0;ki<active;++ki){
    int srcK=split?step:ki;
    for(int ni=0;ni<(bbulk?1:nb);++ni){
     LoadData2DParams ld{};ld.repeatTimes=bbulk?nb:1;
     ld.srcStride=layout?1:kb;ld.ifTranspose=true;
     int src=layout?(srcK*nb+ni)*256:(ni*kb+srcK)*256;
     LoadData(bb[(ki*nb+ni)*256],bl[src],ld);
    }
   }
   if constexpr(Direct){SetFlag<HardEvent::MTE2_M>(ready);WaitFlag<HardEvent::MTE2_M>(ready);}
   a2q.EnQue(aa);b2q.EnQue(bb);aa=a2q.DeQue<half>();bb=b2q.DeQue<half>();
   MmadParams mm{};mm.m=logical?m:mp;mm.k=split?16:(logical?k:kp);
   mm.n=logical?n:np;mm.cmatrixInitVal=(step==0);
   if(step==0) Mmad(acc,aa,bb,mm);else Mmad(acc,aa,bb,acc,mm);
   PipeBarrier<PIPE_M>();++calls;
   debug.SetValue(1,mm.m);debug.SetValue(2,mm.k);debug.SetValue(3,mm.n);
   a2q.FreeTensor(aa);b2q.FreeTensor(bb);
  }
  cq.EnQue(acc);acc=cq.DeQue<float>();FixpipeParamsV220 fp{};
  fp.ndNum=1;fp.mSize=mp;fp.nSize=np;fp.srcStride=mp;fp.dstStride=np;
  Fixpipe(out,acc,fp);cq.FreeTensor(acc);
  if constexpr(!Direct) aq.FreeTensor(al);
  bq.FreeTensor(bl);debug.SetValue(0,calls);
 }
};
