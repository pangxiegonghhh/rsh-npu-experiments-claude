
#ifndef HEADER_ACLRTLAUNCH_E1_DECODE_HKERNEL_H_
#define HEADER_ACLRTLAUNCH_E1_DECODE_HKERNEL_H_



extern "C" uint32_t aclrtlaunch_e1_decode(uint32_t numBlocks, void* stream, void* dv, void* pv, void* jv, void* cv, void* av, void* rv, void* ov, void* zv);

inline uint32_t e1_decode(uint32_t numBlocks, void* hold, void* stream, void* dv, void* pv, void* jv, void* cv, void* av, void* rv, void* ov, void* zv)
{
    (void)hold;
    return aclrtlaunch_e1_decode(numBlocks, stream, dv, pv, jv, cv, av, rv, ov, zv);
}

#endif
