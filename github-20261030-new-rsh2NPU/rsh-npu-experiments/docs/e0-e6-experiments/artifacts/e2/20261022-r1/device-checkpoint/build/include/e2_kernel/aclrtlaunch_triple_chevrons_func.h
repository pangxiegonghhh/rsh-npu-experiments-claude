
#ifndef HEADER_ACLRTLAUNCH_E2_MIX_HKERNEL_H_
#define HEADER_ACLRTLAUNCH_E2_MIX_HKERNEL_H_



extern "C" uint32_t aclrtlaunch_e2_mix(uint32_t numBlocks, void* stream, void* dv, void* pv, void* jv, void* cv, void* bv, void* runv, void* ov, void* snapv, void* tracev, void* donev);

inline uint32_t e2_mix(uint32_t numBlocks, void* hold, void* stream, void* dv, void* pv, void* jv, void* cv, void* bv, void* runv, void* ov, void* snapv, void* tracev, void* donev)
{
    (void)hold;
    return aclrtlaunch_e2_mix(numBlocks, stream, dv, pv, jv, cv, bv, runv, ov, snapv, tracev, donev);
}

#endif
