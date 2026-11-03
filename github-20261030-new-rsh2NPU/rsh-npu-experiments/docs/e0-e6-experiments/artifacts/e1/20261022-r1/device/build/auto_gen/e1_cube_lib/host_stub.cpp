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

static void *g_kernel_handle_aic = nullptr;

struct ascend_kernels {
    uint32_t version;
    uint32_t type_cnt;
    uint32_t aic_type;
    uint32_t aic_len;
    uint32_t aic_file_len;
    uint8_t aic_buf[5648];
} __ascend_kernel_ascend910b2_e1_cube_lib __attribute__ ((section (".ascend.kernel.ascend910b2.e1_cube_lib"))) = {1,1,2,5648,5648,{0}};

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
            if (g_kernel_handle_aic) {
                UnregisterAscendBinary(g_kernel_handle_aic);
                g_kernel_handle_aic = nullptr;
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
        (const char *)__ascend_kernel_ascend910b2_e1_cube_lib.aic_buf,
        __ascend_kernel_ascend910b2_e1_cube_lib.aic_file_len,
        2,
        &g_kernel_handle_aic);
    if (ret != 0) {
        printf("RegisterAscendBinary aic ret %u \n", ret);
    }

    AscendProfRegister();
}





uint32_t launch_and_profiling_e1_cube(uint64_t func_key, uint32_t numBlocks, void* stream, void **args, uint32_t size)
{
    uint64_t startTime;
    const char *name = "e1_cube";
    bool profStatus = GetAscendProfStatus();
    if (profStatus) {
        StartAscendProf(name, &startTime);
    }
    if (g_kernel_handle_aic == nullptr) {
        printf("[ERROR] %s\n", ascendcErrMsg);
        return 0;
    }
    uint32_t ret = LaunchAscendKernel(g_kernel_handle_aic, func_key, numBlocks, args, size, stream);
    if (ret != 0) {
        printf("LaunchAscendKernel ret %u\n", ret);
    }
    if (profStatus) {
        ReportAscendProf(name, numBlocks, 6, startTime);
    }
    return ret;
}

extern "C" uint32_t aclrtlaunch_e1_cube(uint32_t numBlocks, void* stream, void* a, void* b, void* r, void* o, void* c, void* d)
{
    struct {
        alignas(((alignof(void*) + 3) >> 2) << 2) void* a;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* b;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* r;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* o;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* c;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* d;
        alignas(((alignof(void*) + 3) >> 2) << 2) void* __ascendc_overflow;
    } __ascendc_args;

    uint32_t __ascendc_ret;
    constexpr uint32_t __ascendc_overflow_status_size = 8;
    AllocAscendMemDevice(&(__ascendc_args.__ascendc_overflow), __ascendc_overflow_status_size);
    __ascendc_args.a = a;
    __ascendc_args.b = b;
    __ascendc_args.r = r;
    __ascendc_args.o = o;
    __ascendc_args.c = c;
    __ascendc_args.d = d;

    __ascendc_ret = launch_and_profiling_e1_cube(0, numBlocks, stream, (void **)&__ascendc_args, sizeof(__ascendc_args));
    KernelHandleGradUnregister::GetInstance();
    FreeAscendMemDevice(__ascendc_args.__ascendc_overflow);
    return __ascendc_ret;
}
