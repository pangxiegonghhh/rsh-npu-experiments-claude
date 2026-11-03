#pragma once
#include <cstdint>
struct RshConfig {
    int32_t m, k, n, stride, nnz, groups, blocks, sparseRows, cores;
};
