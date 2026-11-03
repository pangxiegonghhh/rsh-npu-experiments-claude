#pragma once
// Cube staging follows Huawei CANN ops-sparse cube_spmm arch22 API usage.
// This experiment uses complete-window ownership; no K-split or atomic add.
#include "kernel_operator.h"
#include "common.h"
using namespace AscendC;

class CubeWork {
public:
    __aicore__ inline void Init(GM_ADDR gp, GM_ADDR refs, GM_ADDR vals,
                              GM_ADDR rhs, GM_ADDR packed, RshConfig cfg,
                              bool useDirectA=false) {
        c=cfg;directA=useDirectA;
        if(directA){directReady=static_cast<event_t>(pipe.FetchEventID(HardEvent::MTE2_M));directReuse=static_cast<event_t>(pipe.FetchEventID(HardEvent::M_MTE2));}
        p.SetGlobalBuffer((__gm__ int64_t*)gp);
        j.SetGlobalBuffer((__gm__ int32_t*)refs);
        a.SetGlobalBuffer((__gm__ half*)vals);
        b.SetGlobalBuffer((__gm__ half*)rhs);
        out.SetGlobalBuffer((__gm__ float*)packed);
        pipe.InitBuffer(a1,2,256*sizeof(half));
        pipe.InitBuffer(a2,2,256*sizeof(half));
        pipe.InitBuffer(b1,2,16*c.stride*sizeof(half));
        pipe.InitBuffer(b2,2,16*c.stride*sizeof(half));
        pipe.InitBuffer(co,1,16*c.stride*sizeof(float));
    }
    __aicore__ inline void Process() {
        for(int32_t g=GetBlockIdx();g<c.groups;g+=c.cores) {
            auto start=p.GetValue(g), end=p.GetValue(g+1);
            if(start==end) continue; // Packed output is zeroed by the caller.
            auto acc=co.AllocTensor<float>();
            for(int64_t t=start;t<end;++t) {
                auto aa=a2.AllocTensor<half>();
                LoadData2DParams ld{};
                ld.repeatTimes=1;ld.ifTranspose=false;
                if(directA) {
                    // E0 only: a[t] is already a single 16x16 ZZ fractal in GM.
                    SetFlag<HardEvent::M_MTE2>(directReuse);WaitFlag<HardEvent::M_MTE2>(directReuse);
                    LoadData(aa,a[t*256],ld);
                    SetFlag<HardEvent::MTE2_M>(directReady);WaitFlag<HardEvent::MTE2_M>(directReady);
                    a2.EnQue(aa);
                } else {
                    auto al=a1.AllocTensor<half>();
                    Nd2NzParams nd{};
                    nd.ndNum=1;nd.nValue=16;nd.dValue=16;nd.srcDValue=16;nd.dstNzNStride=1;
                    DataCopy(al,a[t*256],nd);
                    a1.EnQue(al);al=a1.DeQue<half>();
                    LoadData(aa,al,ld);a2.EnQue(aa);a1.FreeTensor(al);
                }

                auto bl=b1.AllocTensor<half>();
                DataCopyParams cp{};
                cp.blockCount=c.stride/16;cp.blockLen=1;cp.dstStride=15;
                for(int32_t x=0;x<16;++x) {
                    int32_t row=j.GetValue(t*16+x);
                    DataCopy(bl[x*16],b[(int64_t)row*c.stride],cp);
                }
                b1.EnQue(bl);bl=b1.DeQue<half>();
                auto bb=b2.AllocTensor<half>();
                LoadData2DParams ldb{};
                ldb.repeatTimes=c.stride/16;ldb.srcStride=1;ldb.ifTranspose=true;
                LoadData(bb,bl,ldb);b2.EnQue(bb);b1.FreeTensor(bl);

                aa=a2.DeQue<half>();bb=b2.DeQue<half>();
                MmadParams mm{};mm.m=16;mm.k=16;mm.n=c.stride;
                mm.cmatrixInitVal=(t==start);
                if(t==start) Mmad(acc,aa,bb,mm);
                else Mmad(acc,aa,bb,acc,mm);
                PipeBarrier<PIPE_M>();
                a2.FreeTensor(aa);b2.FreeTensor(bb);
            }
            co.EnQue(acc);acc=co.DeQue<float>();
            FixpipeParamsV220 fp{};
            fp.ndNum=1;fp.mSize=16;fp.nSize=c.stride;fp.srcStride=16;fp.dstStride=c.stride;
            Fixpipe(out[(int64_t)g*16*c.stride],acc,fp);
            co.FreeTensor(acc);
        }
    }
private:
    RshConfig c;bool directA=false;event_t directReady{},directReuse{};
    TPipe pipe;
    TQue<TPosition::A1,1>a1;TQue<TPosition::A2,1>a2;
    TQue<TPosition::B1,1>b1;TQue<TPosition::B2,1>b2;TQue<TPosition::CO1,1>co;
    GlobalTensor<int64_t>p;GlobalTensor<int32_t>j;
    GlobalTensor<half>a,b;GlobalTensor<float>out;
};

class VectorWork {
public:
    __aicore__ inline void Init(GM_ADDR ptr,GM_ADDR cols,GM_ADDR vals,GM_ADDR rhs,
                              GM_ADDR rows,GM_ADDR output,RshConfig cfg,int32_t workers) {
        c=cfg;count=workers;
        p.SetGlobalBuffer((__gm__ int32_t*)ptr);j.SetGlobalBuffer((__gm__ int32_t*)cols);
        v.SetGlobalBuffer((__gm__ half*)vals);b.SetGlobalBuffer((__gm__ half*)rhs);
        r.SetGlobalBuffer((__gm__ int32_t*)rows);o.SetGlobalBuffer((__gm__ float*)output);
        pipe.InitBuffer(inBuf,256*sizeof(half));pipe.InitBuffer(castBuf,256*sizeof(float));
        pipe.InitBuffer(accBuf,256*sizeof(float));
    }
    __aicore__ inline void Process() {
        auto input=inBuf.Get<half>();auto converted=castBuf.Get<float>();auto acc=accBuf.Get<float>();
        for(int32_t task=GetBlockIdx();task<c.sparseRows;task+=count) {
            int32_t row=r.GetValue(task);
            Duplicate(acc,0.0f,c.stride);PipeBarrier<PIPE_ALL>();
            for(int32_t q=p.GetValue(row);q<p.GetValue(row+1);++q) {
                auto col=j.GetValue(q);float value=(float)v.GetValue(q);
                DataCopy(input,b[(int64_t)col*c.stride],c.stride);PipeBarrier<PIPE_ALL>();
                Cast(converted,input,RoundMode::CAST_NONE,c.stride);PipeBarrier<PIPE_V>();
                Muls(converted,converted,value,c.stride);PipeBarrier<PIPE_V>();
                Add(acc,acc,converted,c.stride);PipeBarrier<PIPE_ALL>();
            }
            DataCopy(o[(int64_t)row*c.stride],acc,c.stride);PipeBarrier<PIPE_ALL>();
        }
    }
private:
    RshConfig c;int32_t count;
    TPipe pipe;TBuf<TPosition::VECCALC>inBuf,castBuf,accBuf;
    GlobalTensor<int32_t>p,j,r;GlobalTensor<half>v,b;GlobalTensor<float>o;
};

__aicore__ inline RshConfig LoadConfig(GM_ADDR config) {
    GlobalTensor<int32_t> x;x.SetGlobalBuffer((__gm__ int32_t*)config);
    RshConfig c;
    c.m=x.GetValue(0);c.k=x.GetValue(1);c.n=x.GetValue(2);c.stride=x.GetValue(3);
    c.nnz=x.GetValue(4);c.groups=x.GetValue(5);c.blocks=x.GetValue(6);
    c.sparseRows=x.GetValue(7);c.cores=x.GetValue(8);return c;
}

