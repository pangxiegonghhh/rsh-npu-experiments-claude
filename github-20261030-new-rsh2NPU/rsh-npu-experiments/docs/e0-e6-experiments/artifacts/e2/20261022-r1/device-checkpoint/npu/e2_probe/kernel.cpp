#include "kernel_operator.h"
using namespace AscendC;
constexpr event_t EID=static_cast<event_t>(0);
// One AIC + both AIVs. Shared L1 offsets come from the same q/depth contract.
extern "C" __global__ __aicore__ void e2_mix(GM_ADDR dv,GM_ADDR pv,GM_ADDR jv,GM_ADDR cv,GM_ADDR bv,GM_ADDR runv,GM_ADDR ov,GM_ADDR snapv,GM_ADDR tracev,GM_ADDR donev){
 KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_MIX_AIC_1_2);
 GlobalTensor<uint32_t>d,j,c,run,trace,done;GlobalTensor<uint16_t>p;
 GlobalTensor<half>b,snap;GlobalTensor<float>out;
 d.SetGlobalBuffer((__gm__ uint32_t*)dv);p.SetGlobalBuffer((__gm__ uint16_t*)pv);
 j.SetGlobalBuffer((__gm__ uint32_t*)jv);c.SetGlobalBuffer((__gm__ uint32_t*)cv);
 run.SetGlobalBuffer((__gm__ uint32_t*)runv);b.SetGlobalBuffer((__gm__ half*)bv);
 out.SetGlobalBuffer((__gm__ float*)ov);snap.SetGlobalBuffer((__gm__ half*)snapv);
 trace.SetGlobalBuffer((__gm__ uint32_t*)tracev);done.SetGlobalBuffer((__gm__ uint32_t*)donev);
 DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(c);
 uint32_t u=c.GetValue(0),np=c.GetValue(3),orig=c.GetValue(4),tiles=c.GetValue(5);
 uint32_t q=run.GetValue(0),depth=run.GetValue(1),rounds=run.GetValue(2),capture=run.GetValue(3),stall=run.GetValue(4);
 uint32_t packs=(tiles+q-1)/q,readyCount=0,freeCount=0,tileCount=0,role=0;
 if ASCEND_IS_AIV {
  uint32_t sub=GetSubBlockIdx();role=1+sub;
  LocalTensor<uint16_t> ubits(TPosition::VECCALC,0,256);
  LocalTensor<half> ub(TPosition::VECCALC,0,256);
  LocalTensor<half> shared(TPosition::TSCM,0,depth*q*256);
  for(uint32_t epoch=0;epoch<rounds;++epoch){
   for(uint32_t pi=0;pi<packs;++pi){
    uint32_t slot=pi%depth,active=(q<tiles-pi*q?q:tiles-pi*q),owned=0;
    if(pi>=depth){CrossCoreWaitFlag<2,PIPE_MTE3>(2+slot);++freeCount;}
    volatile uint32_t spin=0;for(uint32_t x=0;x<stall*((epoch+sub)%3);++x)spin=spin+x;
    for(uint32_t ix=sub;ix<active;ix+=2){
     uint32_t t=pi*q+ix;uint64_t off=(((uint64_t)d.GetValue(t*4+1)<<32)|d.GetValue(t*4))/2;
     uint32_t h=d.GetValue(t*4+2),z=h&65535,kind=(h>>16)&255,rank=0;
     for(uint32_t x=0;x<256;++x)ubits.SetValue(x,0);
     if(kind==1){
      for(uint32_t r=0;r<16;++r){uint32_t mask=p.GetValue(off+r);
       for(uint32_t k=0;k<16;++k)if(mask&(1u<<k)){uint16_t v=p.GetValue(off+16+rank++);if(epoch%2)v^=0x8000;ubits.SetValue(r*16+k,v);}
      }
     }else{
      for(uint32_t x=0;x<z;++x){uint16_t packed=p.GetValue(off+x/2);uint32_t pos=(packed>>((x%2)*8))&255;
       uint16_t v=p.GetValue(off+(z+1)/2+x);if(epoch%2)v^=0x8000;ubits.SetValue(pos,v);}
     }
     SetFlag<HardEvent::S_MTE3>(EID);WaitFlag<HardEvent::S_MTE3>(EID);
     Nd2NzParams nd{};nd.ndNum=1;nd.nValue=16;nd.dValue=16;nd.srcDValue=16;nd.dstNzC0Stride=16;nd.dstNzNStride=1;
     DataCopy(shared[(slot*q+ix)*256],ub,nd);
     if(capture)DataCopy(snap[(epoch*tiles+t)*256],ub,256);
     SetFlag<HardEvent::MTE3_S>(EID);WaitFlag<HardEvent::MTE3_S>(EID);
     ++owned;++tileCount;
    }
    CrossCoreSetFlag<2,PIPE_MTE3>(slot);++readyCount;
    uint32_t base=((epoch*packs+pi)*3+role)*32;
    uint32_t v[8]={epoch,pi,slot,active,owned,readyCount,freeCount,0xe200u+role};
    for(uint32_t x=0;x<8;++x)trace.SetValue(base+x,v[x]);
   }
   for(uint32_t slot=0;slot<(depth<packs?depth:packs);++slot){CrossCoreWaitFlag<2,PIPE_MTE3>(2+slot);++freeCount;}
  }
 }
 if ASCEND_IS_AIC {
  LocalTensor<half> shared(TPosition::A1,0,depth*q*256);
  LocalTensor<half> bl(TPosition::B1,depth*q*512,16*np);
  LocalTensor<half> aa(TPosition::A2,0,256),bb(TPosition::B2,0,16*np);
  LocalTensor<float> acc(TPosition::CO1,0,16*np);
  for(uint32_t epoch=0;epoch<rounds;++epoch){
   for(uint32_t pi=0;pi<packs;++pi){
    uint32_t slot=pi%depth,active=(q<tiles-pi*q?q:tiles-pi*q);
    CrossCoreWaitFlag<2,PIPE_MTE1>(slot);++readyCount;
    for(uint32_t ix=0;ix<active;++ix){
     uint32_t t=pi*q+ix;
     SetFlag<HardEvent::M_MTE2>(EID);WaitFlag<HardEvent::M_MTE2>(EID);
     SetFlag<HardEvent::M_MTE1>(EID);WaitFlag<HardEvent::M_MTE1>(EID);
     DataCopyParams cp{};cp.blockCount=np/16;cp.blockLen=1;cp.dstStride=15;
     for(uint32_t k=0;k<16;++k){uint32_t ck=t*16+k,row=ck<u?j.GetValue(ck):orig;DataCopy(bl[k*16],b[row*np],cp);}
     SetFlag<HardEvent::MTE2_MTE1>(EID);WaitFlag<HardEvent::MTE2_MTE1>(EID);
     LoadData2DParams la{};la.repeatTimes=1;la.srcStride=1;la.ifTranspose=false;
     LoadData(aa,shared[(slot*q+ix)*256],la);
     LoadData2DParams lb{};lb.repeatTimes=np/16;lb.srcStride=1;lb.ifTranspose=true;LoadData(bb,bl,lb);
     SetFlag<HardEvent::MTE1_M>(EID);WaitFlag<HardEvent::MTE1_M>(EID);
     MmadParams mm{};mm.m=16;mm.k=16;mm.n=np;mm.cmatrixInitVal=t==0;
     if(t==0)Mmad(acc,aa,bb,mm);else Mmad(acc,aa,bb,acc,mm);
     PipeBarrier<PIPE_M>();++tileCount;
    }
    CrossCoreSetFlag<2,PIPE_MTE1>(2+slot);++freeCount;
    uint32_t base=((epoch*packs+pi)*3)*32;
    uint32_t v[8]={epoch,pi,slot,active,active,readyCount,freeCount,0xe200u};
    for(uint32_t x=0;x<8;++x)trace.SetValue(base+x,v[x]);
   }
   if(tiles){
    SetFlag<HardEvent::M_FIX>(EID);WaitFlag<HardEvent::M_FIX>(EID);
    FixpipeParamsV220 fp{};fp.ndNum=1;fp.mSize=16;fp.nSize=np;fp.srcStride=16;fp.dstStride=np;
    Fixpipe(out[epoch*16*np],acc,fp);
    SetFlag<HardEvent::FIX_M>(EID);WaitFlag<HardEvent::FIX_M>(EID);
   }else for(uint32_t i=0;i<16*np;++i)out.SetValue(epoch*16*np+i,0.0f);
  }
 }
 PipeBarrier<PIPE_ALL>();
 uint32_t values[8]={rounds,packs,readyCount,freeCount,tileCount,role,q,depth};
 for(uint32_t x=0;x<8;++x)done.SetValue(role*32+x,values[x]);
 DataCacheCleanAndInvalid<uint32_t,CacheLine::ENTIRE_DATA_CACHE>(done);
}
extern "C" void e2_launch(void*s,void*d,void*p,void*j,void*c,void*b,void*r,void*o,void*a,void*t,void*z){
 e2_mix<<<1,nullptr,s>>>((GM_ADDR)d,(GM_ADDR)p,(GM_ADDR)j,(GM_ADDR)c,(GM_ADDR)b,(GM_ADDR)r,(GM_ADDR)o,(GM_ADDR)a,(GM_ADDR)t,(GM_ADDR)z);
}
