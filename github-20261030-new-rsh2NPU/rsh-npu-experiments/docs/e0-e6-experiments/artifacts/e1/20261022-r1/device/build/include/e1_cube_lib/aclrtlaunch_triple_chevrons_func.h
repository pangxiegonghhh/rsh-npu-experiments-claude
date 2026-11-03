
#ifndef HEADER_ACLRTLAUNCH_E1_CUBE_HKERNEL_H_
#define HEADER_ACLRTLAUNCH_E1_CUBE_HKERNEL_H_



extern "C" uint32_t aclrtlaunch_e1_cube(uint32_t numBlocks, void* stream, void* a, void* b, void* r, void* o, void* c, void* d);

inline uint32_t e1_cube(uint32_t numBlocks, void* hold, void* stream, void* a, void* b, void* r, void* o, void* c, void* d)
{
    (void)hold;
    return aclrtlaunch_e1_cube(numBlocks, stream, a, b, r, o, c, d);
}

#endif
