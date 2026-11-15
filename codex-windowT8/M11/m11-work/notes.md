# M11 执行笔记

- 用户指定：https://github.com/pangxiegonghhh/rsh-npu-experiments-claude/tree/codex-window/codex-windowT8
- 本地起点：main；两份未跟踪论文 PDF，保留。
- 根 CLAUDE.md 已读；现有第一层结果、旧仓库目录不可改写。

## 设备接管
- 用户覆盖旧M8实例隔离限制，复用同一实例。平台4元/小时，启动后运行中。
- 容器 f295d978bae1，物理NPU1，PCI0000:01:00.0，NPU空闲。
- Jupyter终端可用，直接无认证API请求返回403，未尝试提取cookie或更改访问权限。
- Chrome上传工具要求扩展启用Allow access to file URLs；已向用户发出配置说明并等待。
- 剪贴板泛读被自动审核拒绝（可能暴露旧敏感内容），已放弃，未读剪贴板；改用页面可见信息与Jupyter终端。
- 新产物均在m11-work，资料包不改；远端仅新目录。
- CPU working-set审计发现随机大gap会使2GiB源池里的唯一有效行不足4倍L2；正式计时前改为seed固定的随机1/2行gap，保留不等间距，并逐格验证216格cold/hot容量。

## 编译与传输
- 原生浏览器文件选择器可上传，不依赖扩展file URLs权限。用户随后已启用此权限，浏览器短暂断连后恢复（浏览器ID4）。
- 4.7MB全输入包遇HTTP413，未上传成功。改为102824B可重建源码包，含独立Cora参考原件；远端包SHA256 bef0bb17a11a118e66fafa63b10bf96387c504ce924a2162ac3cb79991c55907 已匹配。
- 远端306配置、66CPU布局格、216工作集格重建全部PASS。
- 首编译失败：CANN9.0无HardEvent::MTE1_S。失败源码/日志保存failures/compile-v1，修为MTE1_M后M_S间接等待；同时显式指定std::min<uint64_t>规避Linux整数类型推导差异。
- 第二轮编译成功，100% Built target t8_micro。
- 已启动gate-v1（198热数据配置，单核，完整结果捕获）；正式计时尚未开始。

## 回传通道（已验证）
- 浏览器tar下载ERR_BLOCKED_BY_CLIENT；原生Chrome点击确认是客户端拦截，无新下载记录。未禁用防护，未伪装归档为其他文件类型。
- 标准文件接口无认证返回302登录。通过Jupyter自身CLI核对本实例现有token，标准Authorization读取测试归档返回200。
- transfer-probe.tar.gz为真实7,066字节tar，远端/本机SHA一致。内部3份编译源码与本地逐字节一致。未执行下载二进制。
- 临时认证header在/private/tmp/m11-jupyter-auth.header（0600），不写入仓库、报告或归档；实验回收完毕必须删除该文件和认证响应临时文件。
- environment/processes.txt扫描未包含该登录token。
- 当前阶段3已接受16/20，无作废（上海18:43左右）。


## M11 最终完成（2026-11-15）
设备全部完成并回收，平台已关机复核。45,920条原时钟、204,631文件SHA均PASS，1,104项计时前检查+594项计时后地址复核PASS。主格6/8有条件优势，FP16/N128负结果与FP32 A性能退化均保留。完整报告：/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work/2026-11-15--t8--r11--ordinary-copy-ablation.md。当前无运行任务，勿无故重启实例。临时认证文件已删除。
