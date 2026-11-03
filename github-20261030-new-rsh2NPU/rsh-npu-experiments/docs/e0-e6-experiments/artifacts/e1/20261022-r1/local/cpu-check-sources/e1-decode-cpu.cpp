#include "e1-kernel-stub.h"
using namespace AscendC;
extern "C" __global__ __aicore__ void e1_decode(GM_ADDR dv,GM_ADDR pv,GM_ADDR jv,GM_ADDR cv,GM_ADDR av,GM_ADDR rv,GM_ADDR ov,GM_ADDR zv){
 KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_AIV_ONLY);
 TPipe pipe;GlobalTensor<uint32_t>d,j,c,z;GlobalTensor<uint16_t>p,a;GlobalTensor<int32_t>refs;GlobalTensor<uint32_t>out;
 d.SetGlobalBuffer((__gm__ uint32_t*)dv);p.SetGlobalBuffer((__gm__ uint16_t*)pv);j.SetGlobalBuffer((__gm__ uint32_t*)jv);c.SetGlobalBuffer((__gm__ uint32_t*)cv);
 DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(d);
 a.SetGlobalBuffer((__gm__ uint16_t*)av);refs.SetGlobalBuffer((__gm__ int32_t*)rv);out.SetGlobalBuffer((__gm__ uint32_t*)ov);z.SetGlobalBuffer((__gm__ uint32_t*)zv);
 uint32_t u=c.GetValue(0),kp=c.GetValue(1),np=c.GetValue(3),orig=c.GetValue(4),tiles=c.GetValue(5);
 TBuf<TPosition::VECCALC>ab,rb,ob;pipe.InitBuffer(ab,16*kp*2);pipe.InitBuffer(rb,kp*4);pipe.InitBuffer(ob,16*np*4);
 auto aa=ab.Get<uint16_t>();auto rr=rb.Get<int32_t>();auto oo=ob.Get<uint32_t>();
 for(uint32_t i=0;i<16*kp;++i)aa.SetValue(i,0);
 for(uint32_t i=0;i<kp;++i)rr.SetValue(i,i<u?(int32_t)j.GetValue(i):(int32_t)orig);
 uint32_t total=0;
 for(uint32_t t=0;t<tiles;++t){
  uint64_t off=((uint64_t)d.GetValue(t*4+1)<<32)|d.GetValue(t*4);off/=2;
  uint32_t h=d.GetValue(t*4+2),nnz=h&65535,kind=(h>>16)&255,vk=h>>24,rank=0;
  for(uint32_t r=0;r<16;++r){
   uint32_t mask=kind==1?p.GetValue(off+r):0;
   for(uint32_t k=0;k<16;++k){uint16_t value=0;
    if(kind==0)value=p.GetValue(off+r*16+k);
    else if(kind==3){if(k<vk)value=p.GetValue(off+r*vk+k);}
    else if(kind==1){if(mask&(1u<<k)){value=p.GetValue(off+16+rank);++rank;}}
    aa.SetValue(r*kp+t*16+k,value);
   }
  }
  if(kind==2){uint32_t prefix=(nnz+1)/2;
   for(uint32_t q=0;q<nnz;++q){uint16_t w=p.GetValue(off+q/2);uint32_t pos=(w>>((q%2)*8))&255;
    aa.SetValue((pos/16)*kp+t*16+pos%16,p.GetValue(off+prefix+q));}
  }
  total+=nnz;
 }
 event_t scalarReady=static_cast<event_t>(pipe.FetchEventID(HardEvent::S_MTE3));
 SetFlag<HardEvent::S_MTE3>(scalarReady);WaitFlag<HardEvent::S_MTE3>(scalarReady);
 DataCopy(a,aa,16*kp);DataCopy(refs,rr,kp);
 if(u==0){for(uint32_t i=0;i<16*np;++i)oo.SetValue(i,0);SetFlag<HardEvent::S_MTE3>(scalarReady);WaitFlag<HardEvent::S_MTE3>(scalarReady);DataCopy(out,oo,16*np);}
 PipeBarrier<PIPE_ALL>();z.SetValue(0,1);z.SetValue(1,tiles);z.SetValue(2,total);z.SetValue(3,u);DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(z);
}
