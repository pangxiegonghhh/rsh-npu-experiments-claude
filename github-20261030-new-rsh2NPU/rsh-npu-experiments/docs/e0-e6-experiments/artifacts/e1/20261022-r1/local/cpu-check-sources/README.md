# 本地CPU适配检查

保存实际执行过的本地验证器/标量解码器适配源码。decoder函数体取自本轮decode.cpp，替换的仅是设备API内存stub和launch包装；Input验证器从实际host.cpp截取。适配代码不是Ascend模拟器，不能验证CANN编译、DMA/事件或跨核行为。

可使用clang++ -std=c++17 -O2编译e1-host-validation.cpp，向其传入local/inputs/下的案例目录；16个非法目录在local/invalid/。以-shared -fPIC编译e1-decode-cpu.cpp后可通过ctypes调用e1_decode，对照独立原A/原列oracle。设备真实结果另见封存device目录及独立重放JSON。
