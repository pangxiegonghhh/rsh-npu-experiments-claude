#ifndef __KERNEL__KERNEL_FUN_H__
#define __KERNEL__KERNEL_FUN_H__

#undef __global__
#define __global__ inline
#define e2_mix e2_mix_origin
#include "/data/e2-20261022-r1/npu/e2_probe/kernel.cpp"

#undef e2_mix
#undef __global__
#if ASCENDC_CPU_DEBUG
#define __global__
#else
#define __global__ __attribute__((cce_kernel))
#endif

#ifndef ONE_CORE_DUMP_SIZE
#define ONE_CORE_DUMP_SIZE 1048576 * 1
#endif

extern "C" __global__ [aicore] void auto_gen_e2_mix_kernel(
GM_ADDR ffts_addr, __attribute__((cce_global)) uint8_t* dv, __attribute__((cce_global)) uint8_t* pv, __attribute__((cce_global)) uint8_t* jv, __attribute__((cce_global)) uint8_t* cv, __attribute__((cce_global)) uint8_t* bv, __attribute__((cce_global)) uint8_t* runv, __attribute__((cce_global)) uint8_t* ov, __attribute__((cce_global)) uint8_t* snapv, __attribute__((cce_global)) uint8_t* tracev, __attribute__((cce_global)) uint8_t* donev, GM_ADDR overflow_status) {
    icache_preload(1);
    if (ffts_addr != nullptr) {
        set_ffts_base_addr((uint64_t)ffts_addr);
    }
#ifdef ASCENDC_TIME_STAMP_ON
    AscendC::PrintTimeStamp(static_cast<uint32_t>(AscendC::TimeStampId::TIME_STAMP_WRAP_FFTS_ADDR));
#endif
#if defined(HAVE_WORKSPACE)
    GM_ADDR workspace_param;
    GM_ADDR workspace_usr;
#if defined(HAVE_TILING)
    workspace_param = tracev;
#else
    workspace_param = donev;
#endif
    if (workspace_param == nullptr) {
        return;
    }
    AscendC::SetSysWorkspaceForce(workspace_param);
    workspace_usr = AscendC::GetUserWorkspace(workspace_param);
#if defined(REGIST_MATMUL_OBJ) || defined(__MIX_CORE_MACRO__)
    if constexpr (g_coreType == AscendC::AIC) {
        matmul::clearWorkspace(workspace_param);
#ifdef ASCENDC_TIME_STAMP_ON
        AscendC::PrintTimeStamp(static_cast<uint32_t>(AscendC::TimeStampId::TIME_STAMP_WRAP_CLEAR_WK_SPAC));
#endif
    }
#endif
#if defined(HAVE_TILING)
    tracev = workspace_usr;
#else
    donev = workspace_usr;
#endif
#endif
    e2_mix_origin(dv, pv, jv, cv, bv, runv, ov, snapv, tracev, donev);
#if defined(ASCENDC_DUMP) && defined(ASCENDC_DEBUG)
    AscendC::WriteBackOverflow(overflow_status);
#endif
#if defined(__DAV_C310__)
    pipe_barrier(PIPE_ALL);
    dsb(mem_dsb_t::DSB_ALL);
    dci();
#endif
}

#if defined(__DAV_C220_CUBE__) || defined(__DAV_C310_CUBE__)
static const struct FunLevelMixCoreType e2_mix_mix_aic_section __attribute__ ((used, section (".ascend.meta.e2_mix_0_mix_aic"))) = { { {F_TYPE_KTYPE, sizeof(unsigned int)}, K_TYPE_MIX_AIC_MAIN}, {{F_TYPE_MIX_TASK_RATION, sizeof(unsigned int)}, 1, 2} };
#endif
#if defined(__DAV_C220_VEC__) || defined(__DAV_C310_VEC__)
static const struct FunLevelMixCoreType e2_mix_mix_aiv_section __attribute__ ((used, section (".ascend.meta.e2_mix_0_mix_aiv"))) = { { {F_TYPE_KTYPE, sizeof(unsigned int)}, K_TYPE_MIX_AIC_MAIN}, {{F_TYPE_MIX_TASK_RATION, sizeof(unsigned int)}, 1, 2} };
#endif
#endif
