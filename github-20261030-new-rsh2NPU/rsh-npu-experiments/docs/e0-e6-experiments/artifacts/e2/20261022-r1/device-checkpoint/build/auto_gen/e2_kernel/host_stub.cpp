#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <dlfcn.h>
#include <securec.h>

#ifndef ASCENDC_DUMP
#define ASCENDC_DUMP 1
#endif

#if defined(ASCENDC_DUMP) && (ASCENDC_DUMP == 0)
    #undef ASCENDC_DUMP
#endif

static char ascendcErrMsg[1024] = {0};

static void *g_kernel_handle = nullptr;

struct ascend_kernels {
    uint32_t version;
    uint32_t type_cnt;
    uint32_t mix_type;
    uint32_t mix_len;
    uint32_t mix_file_len;
    uint8_t mix_buf[5312];
} __ascend_kernel_ascend910b2_e2_kernel __attribute__ ((section (".ascend.kernel.ascend910b2.e2_kernel"))) = {1,1,0,5312,5312,{0}};

extern "C" {
uint32_t RegisterAscendBinary(const char *fileBuf, size_t fileSize, uint32_t type, void **handle);
uint32_t LaunchAscendKernel(void *handle, const uint64_t key, const uint32_t numBlocks, void **args,
                            uint32_t size, const void *stream);
uint32_t GetAscendCoreSyncAddr(void **addr);
int UnregisterAscendBinary(void *hdl);
void StartAscendProf(const char *name, uint64_t *startTime);
void ReportAscendProf(const char *name, uint32_t numBlocks, uint32_t taskType, const uint64_t startTime);
bool GetAscendProfStatus();
uint32_t AllocAscendMemDevice(void **devMem, uint64_t size);
uint32_t FreeAscendMemDevice(void *devMem);
bool AscendCheckSoCVersion(const char *socVersion, char* errMsg);
void AscendProfRegister();
uint32_t GetCoreNumForMixVectorCore(uint32_t *aiCoreNum, uint32_t *vectorCoreNum);
uint32_t LaunchAscendKernelForVectorCore(const char *opType, void *handle, const uint64_t key, void **args, uint32_t size,
    const void *stream, bool enableProf, uint32_t aicNumBlocks, uint32_t aivNumBlocks, uint32_t aivNumBlocksOffset);
}

namespace Adx {
    void AdumpPrintWorkSpace(const void *workSpaceAddr, const size_t dumpWorkSpaceSize,
                            void *stream, const char *opType);
}

    class KernelHandleGradUnregister {
    private:
        KernelHandleGradUnregister() {}

    public:
        KernelHandleGradUnregister(const KernelHandleGradUnregister&) = delete;
        KernelHandleGradUnregister& operator=(const KernelHandleGradUnregister&) = delete;

        static KernelHandleGradUnregister& GetInstance() {
            static KernelHandleGradUnregister instance;
            return instance;
        }
        ~KernelHandleGradUnregister(){
            if (g_kernel_handle) {
                UnregisterAscendBinary(g_kernel_handle);
                g_kernel_handle = nullptr;
            }
        }
    };

static void __register_kernels(void) __attribute__((constructor));
void __register_kernels(void)
{
    const char* compileSocVersion = "ascend910b2";
    uint32_t ret;

    bool checkSocVersion = AscendCheckSoCVersion(compileSocVersion, ascendcErrMsg);
    if (!checkSocVersion) {
        return;
    }
    ret = RegisterAscendBinary(
        (const char *)__ascend_kernel_ascend910b2_e2_kernel.mix_buf,
        __ascend_kernel_ascend910b2_e2_kernel.mix_file_len,
        0,
        &g_kernel_handle);
    if (ret != 0) {
        printf("RegisterAscendBinary mix ret %u \n", ret);
    }

    AscendProfRegister();
}





uint32_t launch_and_profiling_e2_mix(uint64_t func_key, uint32_t numBlocks, void* stream, void **args, uint32_t size)
{
    uint64_t startTime;
    const char *name = "e2_mix";
    bool profStatus = GetAscendProfStatus();
    if (profStatus) {
        StartAscendProf(name, &startTime);
    }
    if (g_kernel_handle == nullptr) {
        printf("[ERROR] %s\n", ascendcErrMsg);
        return 0;
    }
    uint32_t ret = LaunchAscendKernel(g_kernel_handle, func_key, numBlocks, args, size, stream);
    if (ret != 0) {
        printf("LaunchAscendKernel ret %u\n", ret);
    }
    if (profStatus) {
        ReportAscendProf(name, numBlocks, 10, startTime);
    }
    return ret;
}

extern "C" uint32_t aclrtlaunch_e2_mix(uint32_t numBlocks, void* stream, void* dv, void* pv, void* jv, void* cv, void* bv, void* runv, void* ov, void* snapv, void* tracev, void* donev)
{
    struct {
        alignas(((alignof(void*) + 3) >> 2) << 2) void* ffts_addr;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* dv;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* pv;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* jv;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* cv;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* bv;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* runv;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* ov;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* snapv;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* tracev;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* donev;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* __ascendc_overflow;
    } __ascendc_args;

    uint32_t __ascendc_ret;
    constexpr uint32_t __ascendc_overflow_status_size = 8;
    AllocAscendMemDevice(&(__ascendc_args.__ascendc_overflow), __ascendc_overflow_status_size);

    void *ffts_addr;
    __ascendc_ret = GetAscendCoreSyncAddr(&ffts_addr);
    if (__ascendc_ret != 0) {
        printf("GetAscendCoreSyncAddr ret %u\n", __ascendc_ret);
        return __ascendc_ret;
    }

    __ascendc_args.ffts_addr = ffts_addr;
    __ascendc_args.dv = dv;
    __ascendc_args.pv = pv;
    __ascendc_args.jv = jv;
    __ascendc_args.cv = cv;
    __ascendc_args.bv = bv;
    __ascendc_args.runv = runv;
    __ascendc_args.ov = ov;
    __ascendc_args.snapv = snapv;
    __ascendc_args.tracev = tracev;
    __ascendc_args.donev = donev;

    __ascendc_ret = launch_and_profiling_e2_mix(0, numBlocks, stream, (void **)&__ascendc_args, sizeof(__ascendc_args));
    KernelHandleGradUnregister::GetInstance();
    FreeAscendMemDevice(__ascendc_args.__ascendc_overflow);
    return __ascendc_ret;
}
