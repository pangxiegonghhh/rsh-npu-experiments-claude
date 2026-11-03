# E2共享地址与握手协议（实现前冻结）

用户授权启动E2。保持原窗口/分流不变，测试单组1AIC+2AIV，关闭Residual。仅用基本API，无Matmul高阶API事件冲突。

采用官方静态Tensor地址方案：AIC A1和AIV TSCM共同的字节基址0；槽s、包内tile i的地址为(s*q+i)*512。固定B1紧随depth*q*512之后，B1长度32*Np。A2/B2/CO1分别在各自物理存储0；每AIV UB底板512B。由同一q/depth推导，非独立分配后猜测重合。q=1/2/4/8，depth=1/2，地址/大小及512B对齐由host/CPU审计，目标编译和实际输出另验。

AIV按包内tile序号奇偶分工，完整16×16软件展开后UB→TSCM ND2NZ；ready使用mode2/MTE3/flag=s，空闲AIV同样发ready。AIC在MTE1等待ready，逐K16装载与计算后mode2/MTE1/flag=2+s归还槽位。前depth包不等free，此后复用前等free；每轮末尾把全部尚未消费的free令牌排空。每轮重启前计数归零，q包不足和空窗口分别处理。最多2个未消费令牌，低于15计数限制。不会用不适用于A2的mode4或PIPE_S set。

轮内tile值随epoch奇偶改变符号，host外层独立改变A/B符号。每次回收每epoch的完整C、可选UB展开快照、按role隔离128B缓存行的逐包trace和最终计数。capture=0保留同一直接片上供给路径，快照GM仅写不读；不以快照作为Cube输入。单缓冲先验收，再执行双缓冲；不将两个槽等同于已经测得性能重叠。

静态事件使用0号，避开官方保留6/7号；S→MTE3及MTE3→S保护UB写/读，AIC显式控制MTE2→MTE1→M及CO1写回复用。单次进程有超时，失败保留且不把同步超时当数值结果。

来源（2026-10-22核对，目标9.0.0安装包另验）：
- [静态Tensor与地址管理](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/programug/Ascendcopdevg/atlas_ascendc_10_00019.html)
- [UB→TSCM ND2NZ](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_00127.html)
- [CrossCoreSetFlag](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0273.html)
- [CrossCoreWaitFlag](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0274.html)
