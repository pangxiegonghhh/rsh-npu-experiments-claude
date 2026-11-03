#ifndef __DECODE__KERNEL_FUN_H__
#define __DECODE__KERNEL_FUN_H__

#undef __global__
#define __global__ inline
#define e1_decode e1_decode_origin
#include "/data/e1-20261022-r1/npu/e1_probe/decode.cpp"

#undef e1_decode
#undef __global__
#if ASCENDC_CPU_DEBUG
#define __global__
#else
#define __global__ __attribute__((cce_kernel))
#endif

#ifndef ONE_CORE_DUMP_SIZE
#define ONE_CORE_DUMP_SIZE 1048576 * 1
#endif

extern "C" __global__ [aicore] void auto_gen_e1_decode_kernel(
__attribute__((cce_global)) uint8_t* dv, __attribute__((cce_global)) uint8_t* pv, __attribute__((cce_global)) uint8_t* jv, __attribute__((cce_global)) uint8_t* cv, __attribute__((cce_global)) uint8_t* av, __attribute__((cce_global)) uint8_t* rv, __attribute__((cce_global)) uint8_t* ov, __attribute__((cce_global)) uint8_t* zv, GM_ADDR overflow_status) {
#if defined(HAVE_WORKSPACE)
    GM_ADDR workspace_param;
    GM_ADDR workspace_usr;
#if defined(HAVE_TILING)
    workspace_param = ov;
#else
    workspace_param = zv;
#endif
    AscendC::SetSysWorkspaceForce(workspace_param);
    workspace_usr = AscendC::GetUserWorkspace(workspace_param);

#if defined(HAVE_TILING)
    ov = workspace_usr;
#else
    zv = workspace_usr;
#endif
#endif
    e1_decode_origin(dv, pv, jv, cv, av, rv, ov, zv);
#if defined(ASCENDC_DUMP) && defined(ASCENDC_DEBUG)
    AscendC::WriteBackOverflow(overflow_status);
#endif
#if defined(__DAV_C310__)
    pipe_barrier(PIPE_ALL);
    dsb(mem_dsb_t::DSB_ALL);
    dci();
#endif
}

static const struct FunLevelKType e1_decode_section __attribute__ ((used, section (".ascend.meta.e1_decode_0"))) = { { {F_TYPE_KTYPE, sizeof(unsigned int)}, K_TYPE_AIV} };
#endif
