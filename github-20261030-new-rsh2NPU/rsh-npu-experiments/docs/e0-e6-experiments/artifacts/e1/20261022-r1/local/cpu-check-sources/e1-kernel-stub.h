#include <cstdint>
#include <vector>
#include <cstring>
#define __global__
#define __aicore__
#define __gm__
#define GM_ADDR void*
#define KERNEL_TASK_TYPE_DEFAULT(...)
#define KERNEL_TYPE_AIV_ONLY 0
#define PIPE_ALL 0
namespace AscendC {
enum class TPosition{VECCALC};enum class HardEvent{S_MTE3};enum class CacheLine{ENTIRE_DATA_CACHE};using event_t=int;
template<class T>struct GlobalTensor{T*p;void SetGlobalBuffer(T*x){p=x;}T GetValue(uint64_t i)const{return p[i];}void SetValue(uint64_t i,T x){p[i]=x;}};
template<class T>struct LocalTensor{T*p;void SetValue(uint64_t i,T x){p[i]=x;}T GetValue(uint64_t i)const{return p[i];}};
template<TPosition P>struct TBuf{std::vector<uint64_t>v;template<class T>LocalTensor<T>Get(){return {reinterpret_cast<T*>(v.data())};}};
struct TPipe{template<TPosition P>void InitBuffer(TBuf<P>&b,uint32_t n){b.v.resize((n+7)/8);}int FetchEventID(HardEvent){return 0;}};
template<class T>void DataCopy(GlobalTensor<T>d,LocalTensor<T>s,uint32_t n){std::memcpy(d.p,s.p,n*sizeof(T));}
template<int P>void PipeBarrier(){}
template<HardEvent E>void SetFlag(event_t){}
template<HardEvent E>void WaitFlag(event_t){}
template<class T,CacheLine C>void DataCacheCleanAndInvalid(GlobalTensor<T>){}
}
