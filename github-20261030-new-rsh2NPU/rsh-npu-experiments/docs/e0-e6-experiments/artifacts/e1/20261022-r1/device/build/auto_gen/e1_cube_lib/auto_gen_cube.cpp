#ifndef __CUBE__KERNEL_FUN_H__
#define __CUBE__KERNEL_FUN_H__

#undef __global__
#define __global__ inline
#define e1_cube e1_cube_origin
#include "/data/e1-20261022-r1/npu/e1_probe/cube.cpp"

#undef e1_cube
#undef __global__
#if ASCENDC_CPU_DEBUG
#define __global__
#else
#define __global__ __attribute__((cce_kernel))
#endif

#ifndef ONE_CORE_DUMP_SIZE
#define ONE_CORE_DUMP_SIZE 1048576 * 1
#endif

extern "C" __global__ [aicore] void auto_gen_e1_cube_kernel(
__attribute__((cce_global)) uint8_t* a, __attribute__((cce_global)) uint8_t* b, __attribute__((cce_global)) uint8_t* r, __attribute__((cce_global)) uint8_t* o, __attribute__((cce_global)) uint8_t* c, __attribute__((cce_global)) uint8_t* d, GM_ADDR overflow_status) {
#if defined(HAVE_WORKSPACE)
    GM_ADDR workspace_param;
    GM_ADDR workspace_usr;
#if defined(HAVE_TILING)
    workspace_param = c;
#else
    workspace_param = d;
#endif
    AscendC::SetSysWorkspaceForce(workspace_param);
    workspace_usr = AscendC::GetUserWorkspace(workspace_param);

#if defined(HAVE_TILING)
    c = workspace_usr;
#else
    d = workspace_usr;
#endif
#endif
    e1_cube_origin(a, b, r, o, c, d);
#if defined(ASCENDC_DUMP) && defined(ASCENDC_DEBUG)
    AscendC::WriteBackOverflow(overflow_status);
#endif
#if defined(__DAV_C310__)
    pipe_barrier(PIPE_ALL);
    dsb(mem_dsb_t::DSB_ALL);
    dci();
#endif
}

static const struct FunLevelKType e1_cube_section __attribute__ ((used, section (".ascend.meta.e1_cube_0"))) = { { {F_TYPE_KTYPE, sizeof(unsigned int)}, K_TYPE_AIC} };
#endif
