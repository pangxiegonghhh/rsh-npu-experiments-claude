# M11 阶段0源码核对

固定版本：AscendSPMM ca0abfeccf957d938ac8946a987f05aa6e9ec36c；已校验交接提供的 Git blob SHA。以下行号指 upstream-sources/upstream-idmg/spmm_ascend_cube.cpp。

| 项目 | FP16 | FP32 | 源码位置 |
|---|---|---|---|
| B 普通 DataCopy | blockCount=N/16, blockLen=1, srcStride=0,dstStride=15 | blockCount=N/8, 其余相同 | 57–70 |
| B 发法 | 每选中行一次；每16行16次 | 同左 | 240–263 |
| B L1地址 | (j/16)*256+k*16+j%16 | (j/8)*128+k*8+j%8 | 246–248、59–69 |
| B 转置加载 | repeatTimes=N/16,srcStride=1 | 另dstFracGap=N/16−1 | 98–103 |
| A 输入 | 普通DataCopy连续原始列块 | Nd2NzParams 实际启用 | 168–183 |
| A 转置加载 | repeatTimes=SPTILE/16,srcStride=1 | 另dstGap=1 | 188–192 |
| A 尾块 | 先清零后普通搬运 | 整tile与余列分别ND2NZ | 197–235 |

SPTILE=96，ROW_WINDOW=16，MAXD=FP16 1024/FP32 512，源码13/19行；不能将MAXD误当每个M11配置的实际N。host按精度接收FP16/FP32，并按AIC核数分块，见 kernels__op_host__spmm_ascend_cube.cpp:20–34、87–111。extension__custom_op.cpp:1239–1270按列槽存连续16行值；这是原始列块，而非M4预打包的L0A。

【CPU已验】普通按列条法可在保持同一L1布局时，用每个有效段片每个c0特征条一次DataCopy：blockCount=h,blockLen=1,srcStride=N/c0−1,dstStride=0，c0=32/元素字节数。次数为切分到16行tile后的段片数×N/c0。FP32为N/8，不是N/16。末尾补零另计。API调用数不是设备退休指令数。

【源码已核】M4 的A由host按(k/c0)*16*c0+m*c0+k%c0预排GM，直接LoadData到L0A；FP32 repeatTimes=2，禁用HF32。既有gate只证明其有限整数标记逐元素等于CPU参考，不是所有浮点位模式的证明。M11新加原始A列块的ND2NZ链及普通两条stride拷贝重排链；是否正确/是否更快必须设备验收。FP32原始列块并不自动等价于一条连续DataCopy后直接转置。

官方CANN9 basic DataCopy页面已读：https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0103.html 。普通GM→L1块长和间隔以32B计；源/目的不改格式。当前网页同时列较新产品，需以实机9.0头文件交叉核验，尚不将网页当设备验收。

非流水版已复核：kernels__op_kernel__spmm_ascend_cube_aic_without_pipeline.cpp:6 把SPTILE设为16（g=1），MAXD仍按精度1024/512，普通B按行与A FP32 ND2NZ链保持一致。不能把g=1和主版本SPTILE96混合引用。

实机初查：重新开机后容器 f295d978bae1、aarch64，npu-smi显示910B2、物理NPU1、PCI 0000:01:00.0、无运行中NPU进程（与旧M8物理NPU5不同）。SDK根为 /usr/local/Ascend/cann-9.0.0；并非预想的ascend-toolkit/latest/version.cfg，后者文件不存在已记录。环境快照仅新写 /data/t8-m11-20261115/environment。

实机头文件已回收到 sdk-evidence/kernel_struct_data_copy.h，SHA256 f05bcf8a9ad19fc96f7d279a748a1c30ab74709a9d3865e05cc8ba1175ea6b23。普通DataCopyParams见48–73行，srcStride/dstStride是uint16别名（新名srcGap/dstGap）；Nd2NzParams见257行起，910B2所用分支不是新3510/5102分支，srcNdMatrixStride为uint16。因此命令表对stride*N>65535主动拆分，不截断。
