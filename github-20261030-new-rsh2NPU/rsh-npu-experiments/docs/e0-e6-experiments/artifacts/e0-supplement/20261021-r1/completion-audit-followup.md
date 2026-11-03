# E0收尾覆盖审计与补齐

结论：**缺口已补齐，120次逐次验证通过，实例最终已关机，E1未开始。**

## 发现

原7个独立核心配置已做到3进程×10次逐次验证；旧集成rsh_guarded只检查首两次与测量结束，不能证明相邻窗口核心配置的每次中间调用。首尾通过不能替代计划中的逐次验证，因此未放宽门槛，而是恢复同一实例补测。

## 补充方法

新增`npu/e0_probe/repeat_each.cpp`，直接复用未修改的Case/guard检查实现和最终librsh_kernels.a，不改变kernel、窗口、路由或输入结构。常规/直装两路径各3个新进程；每进程M30分解和U17/U37相邻窗口各10次，独立轮换A/B符号，共120次。每次计算后立即校验全部有效输出、完整packed、规定padding和所有GM guard，单独保存该次原始out/packed。

原直接g++链接缺profapi依赖，失败日志保留；随后从已验证的CMake link.txt读取完整链接参数构建全新host。精确命令见[build-command.json](each-call/build-command.json)。父版本源码/6个执行产物及SDK头文件哈希检查未变，平台资源查询也与主轮一致。

## 结果与证据

- [逐次汇总](each-call/summary.json)：6进程、120次全部通过，最大绝对误差0。
- [120条调用记录](each-call/checks.json)包含iteration及A/B符号；[进程与执行命令](each-call/commands.json)记录PID、时间及返回码。
- [独立补充归档](e0-each-call-followup.tar.gz)：98195 B，SHA-256 `fb4a87e09bf1e2ef02f58121be7aeec739ef04467588053995d9636e7bc0ca15`，与远端终端显示一致。265文件，清单覆盖其余264个，本地均校验。
- [本地逐次重放](each-call-local-verification.json)：120次的全部out/packed原始输出及guard独立重放通过，未改动原始证据；新host与执行脚本源码也已与归档逐字节对应。
- [最新关机截图](instance-off-each-call.png)：2026-10-21 21:58:49北京时间保存，已关机、开关0、GPU释放，平台累计1小时27分钟（含首轮及主补测）。

主轮归档保持原样，补充归档与其以parent_archive_sha256关联。大输出Notebook曾触发413保存错误和离开页面确认，阻塞了回收界面；关闭已备份的临时大输出页后，通过直接文件下载完成回收。这属于数据回收过程，不是NPU计算失败。
