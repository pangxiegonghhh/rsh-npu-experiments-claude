"""Freeze reports/evidence only after both registered timing stages finish."""
import hashlib
import json
import subprocess
import tarfile
import time
from pathlib import Path

root=Path(__file__).resolve().parent;main=root.parent/'t8-m4'
def digest_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
while not (root/'formal-driver-v1.rc').exists():time.sleep(10)
assert (root/'formal-driver-v1.rc').read_text().strip()=='0','Replay timing failed; no final report'
assert (main/'formal-driver-v5.rc').read_text().strip()=='0'
for script,cwd in [('analyze_m4.py',main),('evaluate_replay.py',root)]:
    with (cwd/(script+'.log')).open('w') as log:
        subprocess.run(['python3',script],cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
model_file=main/'model-v5-verification.json'
instruction=json.loads(model_file.read_text()) if model_file.exists() else {'status':'MISSING'}
comparison=json.loads((root/'analysis-v1/B0-B1-comparisons.json').read_text())
evaluation=json.loads((root/'analysis-v1/replay-evaluation.json').read_text())
source_groups=[]
for directory,prefix in [(main,'v5'),(root,'v1')]:
    rejected=0;attempts=0;max_valid=0
    for p in (directory/f'results-blocks-{prefix}').glob('b*-accepted.json'):
        journal=json.loads(p.read_text());attempts+=len(journal['attempts'])
        for a in journal['attempts']:
            for r in a['registration']:
                if r['valid']=='1':max_valid=max(max_valid,float(r['drift']))
                else:rejected+=1
    source_groups.append(dict(stage=directory.name,attempts=attempts,rejected_groups=rejected,max_accepted_group_drift=max_valid))

lines=['# T8 M4 实验结果','',
       '实卡：2026-11-15，Ascend910B2 物理 NPU 1，CANN 9.0.0，24 AIC。M5 性能数据来自前一天的物理 NPU 4，两个环境分开保存。','',
       '## 验收与计时','',
       '- 合成设计共 560 个基础几何/精度/缓存点；合并/逐段 × 三种预取配置后 3,360 个逻辑点，完全相同命令与地址调度去重后实跑 2,592 点。24 个首轮与全部全卡用例均通过逐元素、输入、元数据、保护区和运行时调用次数检查。',
       '- 正式重复为 20 个随机块，每点一次预热后一次测量；每个精度/N 组前后五次哨兵中位数，漂移超过 5% 的组保留并排除，最多重试三次。有效热工作集为 32 MiB，冷工作集为至少 1 GiB；L2 查询为 192 MiB。',
       '- 31 个代表点的五轮试跑通过每段 5 ns、ΔR=32 的批量分辨率门槛；最差信噪比约 32.11。计时区间包含供数、MTE1 和 MMAD，最后输出回读在计时之外；正确性阶段捕获每个窗口。',
       '- Cora B0/B1 另有 8 个首轮、40 个全卡回放用例全部通过。正式回放也为 20 个随机块，保留逐次原始值。按每一个真实窗口的 U/R/调用数求预测后相加，再与设备回放比较。','',
       '## 指令与实现范围','',
       f"M4 官方模型指令核验状态：{instruction.get('status')}。完整记录见 model-v5-verification.json。只把成功路径用作指令原语证据；模型时钟不用于性能。运行时计数器是 API 调用计数，不能称作实卡 PMU retired-instruction 计数。",'',
       '初版跨迭代手工 L0B 旗标等待引发 AIC 执行异常；改用深度为二的 B2 队列管理槽复用后全部通过。Cora 初版命令表没有按 N 检查 16 位 srcNdMatrixStride，部分远间距合并发生截断；按字段上限拆分后全部通过。失败源码、参数和日志保留。','',
       '回放沿用真实的 B 行段表，但 A 为固定稠密小块；24 个 AIC 在不重叠的 B 副本上重放相同窗口顺序，以固定热/冷工作集。它检验本微基准的模型迁移，不是完整稀疏 A、单份 Cora 输入的端到端 SpMM 性能。尾块补零调用也计入实际 API 数。','',
       '## G2 与模型核对','',
       '主模型为 T=c+a·U·N·s+b·R；另拟合实际 API 数模型。近间距的等长与偏斜点进入主拟合；远间距 U=64 曲线单独报告。实际 API 数与字节项共线时明确标为不可识别。置信区间来自 20 个随机块的系数变化，描述计时变化；模型失配由残差和真实回放误差单列。',
       '固定的是请求的有效字节数；段布局仍可能改变缓存行流量、ND2NZ 内部分段、标量参数设置和流水重叠。b 是本协议下的有效段数项，没有用流量 PMU 把它分解为纯搬运指令延迟。',
       '', '下表 b 为 24 核并发下的每核等效段成本；模型预测/回放均采用全局设备 makespan 除以所有核的窗口/矩阵数，换算一致。误差要求为 B0、B1 均不超过 15%，并检查逐窗口预测非负。','',
       '| 精度 | N | 缓存 | b（ns，95% 区间） | B0/B1 回放误差 | 实测 B0→B1 降幅 | R 模型通过 |',
       '|---|---:|---|---|---|---|---|']
for row in comparison:
    a=next(r for r in evaluation if (r['dtype'],r['n'],r['cache'],r['order'])==(row['dtype'],row['n'],row['cache'],'B0'))
    b=next(r for r in evaluation if (r['dtype'],r['n'],r['cache'],r['order'])==(row['dtype'],row['n'],row['cache'],'B1'))
    slope=row['b_ns_core_equivalent']
    lines.append(f"| {row['dtype']} | {row['n']} | {row['cache']} | {slope['mean']:.3f} [{slope['low']:.3f}, {slope['high']:.3f}] | {a['R_model']['relative_error']:.1%} / {b['R_model']['relative_error']:.1%} | {row['measured_B0_to_B1_reduction']:.1%} | {'是' if row['R_model_replay_qualified'] else '否'} |")
lines+=['','预测/回放不合格的格子不下 G2 结论。b 的区间含零且段数项占比上界低于 2% 时，按计划报告“没有可测代价”；其余不清楚的格子应增大批量复测一次后再判。b 显著为正且回放合格时，交用户按尚未指定的幅度门槛判断 G2；B0→B1 同时改变 U 与 R，不能把全部降幅归因于段数。','',
        '逐格解释及是否需要复测见 t8-m4-replay/analysis-v1/B0-B1-comparisons.json。本文不把未完成的复测或用户幅度门槛判定写成已完成。','',
        '## 文件','',
        '- analysis-v5/model-fits.json、case-summary.csv：完整拟合和逐点中位数、四分位距、CV。',
        '- t8-m4-replay/analysis-v1/replay-evaluation.json、window-predictions.csv：逐窗口预测、回放误差和可识别性。',
        '- results-check-v5、results-blocks-v5、t8-m4-replay/results-check-v1、results-blocks-v1：原始验收/计时、作废组及重跑轨迹。',
        '- environment-20261115、p0-20261115：本次实卡环境与 P0；旧 k0-r3/p0 是前一天环境。','',
        '漂移登记摘要：','',json.dumps(source_groups,ensure_ascii=False,indent=2),'']
(main/'M4-results-20261115.md').write_text('\n'.join(lines),encoding='utf-8')
(main/'finalization-status.json').write_text(json.dumps(dict(data_collection_complete=True,
    final_G2_requires_review=True,unresolved_retest_cells=[r for r in comparison if r['G2'].startswith('inconclusive')],
    instruction_status=instruction.get('status'),group_quality=source_groups),indent=2))
with (main/'environment-20261115/npu-after.txt').open('w') as log:subprocess.run(['npu-smi','info'],stdout=log,stderr=subprocess.STDOUT)
for directory in (main,root):
    hashes=[]
    for path in sorted(directory.rglob('*')):
        if path.is_file() and path.name not in {'SHA256SUMS','finalize.log','finalize-wrapper.log','finalize.pid','finalize.rc'}:
            digest=digest_file(path)
            hashes.append(digest+'  ./'+path.relative_to(directory).as_posix())
    (directory/'SHA256SUMS').write_text('\n'.join(hashes)+'\n')
archive=root.parent/'t8-m4-evidence-20261115.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for directory in [main,root,root.parent/'p0-20261115',root.parent/'k0-r3/p0']:
        if directory.exists():tar.add(directory,arcname=str(directory.relative_to(root.parent)))
digest=digest_file(archive)
archive.with_suffix('.sha256').write_text(digest+'  '+archive.name+'\n')
print('M4_EVIDENCE_READY',archive,'sha256',digest,flush=True)
