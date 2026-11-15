"""Render M11 verified statistics and a local research report; no device access."""
from pathlib import Path
import csv
import json
import os
import numpy as np


def finalize(root: Path) -> None:
    os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/m11-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    work = Path(__file__).resolve().parent
    out = root / 'analysis-output'
    figs = out / 'figures'
    read = lambda name: json.loads((out / name).read_text())
    contrasts = read('paired-contrasts.json')
    primary = [r for r in contrasts if r['primary']]
    reorder = read('reordering-ratios.json')
    micro = read('micro-fits.json')
    curves = read('micro-per-block-fits.json')
    apairs = read('A-chain-paired-contrasts.json')
    decision = read('decision.json')
    with (out / 'stage3-summary.csv').open() as stream:
        summary = {r['case']: r for r in csv.DictReader(stream)}
    assert len(primary) == 16 and decision['descriptive_over20_count'] == 6

    # Keep mean-curve goodness of fit distinct from per-block goodness of fit.
    groups = {}
    for r in curves:
        groups.setdefault((r['stage'], r['a_mode'], r['case']), []).append(r)
    quality = []
    for (stage, mode, case), rr in sorted(groups.items()):
        assert len(rr) == 20
        points = np.asarray([r['raw_points'] for r in rr])
        assert np.all(points[:, :, 0] == points[0, :, 0])
        x = points[0, :, 0]
        y = points[:, :, 1].mean(axis=0)
        k, intercept = np.polyfit(x, y, 1)
        r2 = 1 - np.sum((k*x+intercept-y)**2) / np.sum((y-y.mean())**2)
        quality.append(dict(stage=stage, a_mode=mode, case=case,
                            mean_curve_r2=float(r2), mean_curve_k_us=float(k),
                            mean_curve_intercept_us=float(intercept),
                            mean_us_by_batch=y.tolist(), batch=x.tolist()))
    (out / 'micro-mean-curve-quality.json').write_text(json.dumps(quality, indent=2))

    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'savefig.facecolor': 'white'})
    colors = ['#536773', '#157e95', '#c26923']
    def save(fig, name):
        fig.savefig(figs / f'{name}.pdf', bbox_inches='tight')
        fig.savefig(figs / f'{name}.png', dpi=180, bbox_inches='tight')
        plt.close(fig)

    labels = sorted({r['baseline'] for r in primary})
    short = [s.replace('cora-B1-', '').replace('-p0', '').replace('-n', '\nN=').replace('-hot', '\nhot').replace('-cold', '\ncold') for s in labels]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), layout='constrained')
    for ax, p in zip(axes, [1, 2]):
        rr = [next(r for r in primary if r['baseline'] == s and r['case'].endswith(f'p{p}')) for s in labels]
        means = np.array([r['ratio_of_means'] for r in rr])
        ci = np.array([r['ratio_of_means_paired_bootstrap_ci95'] for r in rr])
        ax.errorbar(range(8), means, yerr=np.array([means-ci[:, 0], ci[:, 1]-means]),
                    fmt='o', capsize=3, color=colors[p])
        for x, y in enumerate(means):
            ax.annotate(f'{y:.3f}', (x, y), xytext=(0, 9), textcoords='offset points', ha='center', fontsize=8)
        ax.axhline(1, color='#666666', ls='--', lw=1, label='Equal time')
        ax.axhline(.8, color='#222222', ls=':', lw=1, label='20% lower time')
        ax.set_xticks(range(8), short, fontsize=8)
        ax.set_ylabel('Ordinary / ND2NZ mean time (lower is better)')
        ax.set_title(f'p{p}: ' + ('one copy per row' if p == 1 else 'one copy per feature stripe'))
        ax.set_ylim((.45, 1.47) if p == 1 else (0, 14))
        ax.grid(axis='y', alpha=.18)
    axes[0].legend(loc='lower left', fontsize=8)
    fig.suptitle('Cora B1: eight registered primary cells; 20 paired blocks\nPointwise paired bootstrap 95% CI; panels use different y scales')
    save(fig, 'figure-01-main-comparison')

    fig, axes = plt.subplots(2, 3, figsize=(13, 7), layout='constrained')
    keys = [(n, cache) for n in [16, 128, 256] for cache in ['hot', 'cold']]
    for row, dtype in enumerate(['FP16', 'FP32']):
        for p in range(3):
            ax = axes[row, p]
            rr = [next(r for r in reorder if r['case'] == f'cora-B0-{dtype}-n{n}-{cache}-p{p}') for n, cache in keys]
            mean = np.array([r['ratio_of_means'] for r in rr])
            ci = np.array([r['ratio_of_means_paired_bootstrap_ci95'] for r in rr])
            ax.errorbar(range(6), mean, yerr=[mean-ci[:, 0], ci[:, 1]-mean], fmt='o', color=colors[p], capsize=3)
            ax.axhline(1, color='#666666', ls='--', lw=1)
            ax.set_xticks(range(6), [f'{n}\n{c}' for n, c in keys], fontsize=8)
            ax.set_title(f'{dtype} / ' + ['ND2NZ', 'ordinary row', 'ordinary stripe'][p])
            ax.set_ylim(.9, 2.8)
            ax.grid(axis='y', alpha=.18)
            if p == 0:
                ax.set_ylabel('B0 / B1 mean time (>1 favors B1)')
    fig.suptitle('Reordering under each B path; U and R change together\n20 paired blocks; pointwise paired bootstrap 95% CI; common y scale')
    # Use one common range covering every measured interval; no clipped outliers.
    ymax = max(r['ratio_of_means_paired_bootstrap_ci95'][1] for r in reorder)
    for ax in axes.flat:
        ax.set_ylim(.9, max(2, ymax*1.06))
    save(fig, 'figure-02-reordering')

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
    for i, dtype in enumerate(['FP16', 'FP32']):
        for j, n in enumerate([128, 256]):
            ax = axes[i, j]
            for cache, ls in [('hot', '-'), ('cold', '--')]:
                rr = [next(r for r in contrasts if r['case'] == f'synthetic-r{rnum}-{dtype}-n{n}-{cache}-p1') for rnum in [1, 4, 16, 64]]
                mean = np.array([r['ratio_of_means'] for r in rr])
                ci = np.array([r['ratio_of_means_paired_bootstrap_ci95'] for r in rr])
                ax.errorbar(range(4), mean, yerr=[mean-ci[:, 0], ci[:, 1]-mean],
                            fmt='o'+ls, capsize=3, label=cache)
            ax.axhline(1, color='#555555', ls=':', lw=1)
            ax.set_xticks(range(4), [1, 4, 16, 64])
            ax.set_xlabel('Number of runs R (U=64)')
            ax.set_ylabel('Ordinary row / ND2NZ mean time')
            ax.set_ylim(0, 2.05)
            ax.set_title(f'{dtype}, N={n}')
            ax.grid(axis='y', alpha=.18)
    axes[0, 0].legend()
    fig.suptitle('Synthetic layout sensitivity: relative path preference changes with R\nFixed-seed random gaps; 20 paired blocks; pointwise bootstrap 95% CI')
    save(fig, 'figure-03-R-sensitivity')

    catalog = '''# 图目录

所有图为真实45,920条计时观测的派生结果；PDF与PNG同名。误差条均为20个时间区组成对bootstrap、10,000次重采样的平均耗时比点95%CI；不是跨矩阵泛化区间，也没有多重区间覆盖保证。细小误差条可能被标记遮住，精确端点见JSON。

## figure-01-main-comparison

- 目的：核查Cora B1的8个预登记高N格，明确两种普通供数路径的结果。
- 来源：paired-contrasts.json，primary=true。
- 图注：左右分别为按行p1、按条p2，使用不同纵轴范围；1表示等时，0.8表示降时20%。每条路径单独保留，未画两选一后的置信区间。
- 观察：p1在6/8格低于0.8，FP16/N128两格超过1.3；p2在全部主格耗时约为ND的9–13倍。
- 解释与决策：支持有条件改用按行路径，不能把六格优势推广到全部精度/N。
- 检查：应同时看精度、N、冷热及纵轴刻度；不能称为完整SpMM或孤立单核延迟。

## figure-02-reordering

- 目的：换供数方式后重排仍有多少价值。
- 来源：reordering-ratios.json；每条路径/精度独立面板，共用纵轴。
- 图注：纵轴B0/B1平均耗时比，大于1表示B1更快；横轴为N与冷热。
- 观察：普通按行在六个获胜高N格仍有约1.48倍重排收益。
- 解释与决策：保留降低供数行数/补齐tile的证据；U、R、T同时变化，不能当纯R因果效应。
- 检查：勿将B0/B1加速比写成百分比降幅；勿混用三条路径。

## figure-03-R-sensitivity

- 目的：验证按行路径调用数不随R变化，是否就能说R不再影响供数决策。
- 来源：paired-contrasts.json中synthetic、p1；U固定64，R=1/4/16/64。
- 图注：按行/ND平均耗时比，hot实线、cold虚线。随机间距与地址跨度随布局变化，不是纯固定指令开销测量。
- 观察：hot高N格在R≤16时按行比ND慢，在R64时按行更快；路径偏好发生翻转。
- 解释与决策：即使按行自身对R不敏感，R仍可影响与ND比较后的选择，不能删去段结构信息。
- 检查：仅本合成网格；不将曲线当任意矩阵的通用选择器或硬件t模型。
'''
    (out / 'figure-catalog.md').write_text(catalog)
    appendix = out / 'stats-appendix.md'
    extra = '''
- 阶段3哨兵留存每组前后5次的中位数与漂移，未留存这5次逐项原值；20轮主观测完整。阶段2与A共享区组保留外部哨兵的各5条原值。
- 所有路径共用M4容量上限gmax，不曾逐路径搜索最优队列深度。因此本实验不能宣称普通路径、ND2NZ或全包络实现已全局最优。
- 初始1104项正确性检查在计时前；594项更强完整地址复核在计时后，链接同一kernel、确认正式计时binary未改。两者时序不能混写。
'''
    if '阶段3哨兵留存' not in appendix.read_text():
        appendix.write_text(appendix.read_text() + extra)

    claims = '''

## Additional Claim Candidates

- Claim: 在预登记的Cora B1高N八格中，普通按行路径有六格平均耗时降低超过20%。
  - Source evidence: decision.json、paired-contrasts.json；20共享时间区组，六格点CI上界也小于0.8。
  - Allowed wording: 本M4回放骨架与共同gmax下，六格降低25.35%–42.07%，满足至少5/8的描述性触发条件，优势有条件成立。
  - Forbidden stronger wording: 普通搬运全面优于ND2NZ；全部稀疏SpMM至少快20%；已找到最优实现。
  - Uncertainty: 只有Cora、固定稠密A消费、两选一偏差、时间区组相关性、没有跨芯片重复。
  - Next check: 在独立矩阵和真实稀疏A端到端内核中验证，另做逐路径g调优。
  - Decision: keep

- Claim: 普通按行供数下，Cora重排在六个高N优势格仍带来约1.48倍加速。
  - Source evidence: reordering-ratios.json的p1；U64下R-sensitivity.json与figure-03。
  - Allowed wording: B1降低本回放的总供数工作，U/R/T同时变化；R仍影响ND与按行的相对选择。
  - Forbidden stronger wording: 段数已无价值；重排收益完全由降行数或纯R决定。
  - Uncertainty: 未独立干预U/R/T；synthetic地址与缓存布局随R变化。
  - Next check: 后续需要时分离U、T和R的控制变量。
  - Decision: keep

- Claim: FP32原始列块A的普通两stride搬运链可正确执行，但在本实现中耗时约为ND链的5.5倍。
  - Source evidence: GATES-PASSED.json、STRONG-ADDRESS-GATES.json、A-chain-paired-contrasts.json。
  - Allowed wording: 区分M4 host预打包直装与原始列块；当前FP32普通链正确，性能不支持直接替换ND链。
  - Forbidden stronger wording: FP32一条连续普通拷贝已验收；硬件无法普通搬运；FP16方案无条件推广到FP32。
  - Uncertainty: 只测试一个两stride普通实现，不是所有可行FP32布局。
  - Next check: 若更改第四层FP32路线，再比较替代布局的完整开销。
  - Decision: keep
'''
    analysis = out / 'analysis-report.md'
    if '## Additional Claim Candidates' not in analysis.read_text():
        analysis.write_text(analysis.read_text() + claims)

    def ci(r):
        low, high = r['ratio_of_means_paired_bootstrap_ci95']
        return f'[{low:.4f}, {high:.4f}]'
    def table(header, rows):
        return '\n'.join(['| ' + ' | '.join(header) + ' |', '|'+ '|'.join(['---']*len(header))+'|'] + ['| '+' | '.join(map(str, r))+' |' for r in rows])
    mainrows = []
    for r in primary:
        if not r['case'].endswith('p1'):
            continue
        name = r['baseline']
        s0, s1 = summary[name], summary[r['case']]
        mainrows.append([name.replace('cora-B1-', '').replace('-p0', ''),
                         f"{float(s0['mean']):.4f} ± {float(s0['sd']):.4f}",
                         f"{float(s1['mean']):.4f} ± {float(s1['sd']):.4f}",
                         f"{r['ratio_of_means']:.4f}", ci(r), f"{r['time_drop_pct']:.2f}%", f"{r['speedup_ratio_of_means']:.3f}×"])
    n16rows = [[r['case'].replace('cora-B1-', ''), f"{r['ratio_of_means']:.5f}", ci(r), f"{r['time_drop_pct']:.2f}%"] for r in contrasts if r['case'].startswith('cora-B1-') and '-n16-' in r['case']]
    arows = []
    for r in apairs:
        q = r['ordinary_over_nd']
        arows.append([r['case'].replace('micro-a-chain-', ''), f"{q['second_mean_us']:.5f}", f"{q['first_mean_us']:.5f}", f"{q['ratio_of_means']:.3f}", ci(q)])
    rrows = []
    for r in reorder:
        if '-p1' in r['case']:
            rrows.append([r['case'].replace('cora-B0-', '').replace('-p1', ''), f"{r['ratio_of_means']:.4f}", ci(r), f"{100*(1-1/r['ratio_of_means']):.2f}%"])
    mrows = []
    for dtype in ['FP16', 'FP32']:
        for n in [16, 128, 256]:
            names = [f'micro-plain-{dtype}-n{n}', f'micro-transpose-{dtype}-n{n}'] + [f'micro-copy-{dtype}-n{n}-h16-p{p}' for p in range(3)]
            mrows.append([dtype, n] + [f"{next(r['mean'] for r in micro if r['stage']=='stage2' and r['case']==name):.6f}" for name in names])
    synrows = []
    for dtype in ['FP16', 'FP32']:
        for n in [128, 256]:
            synrows.append([dtype, n] + [f"{next(r['ratio_of_means'] for r in contrasts if r['case']==f'synthetic-r{rn}-{dtype}-n{n}-hot-p1'):.4f}" for rn in [1, 4, 16, 64]])
    qmin = min(r['mean_curve_r2'] for r in quality)
    bmin = min(r['r2'] for r in curves)
    lowfits = sum(r['mean_r2'] < .999 for r in micro)
    report = f'''---
type: results-report
date: 2026-11-15
experiment_line: t8
round: 11
purpose: ordinary-copy-ablation
status: complete
source_artifacts:
  - recovered-evidence/analysis-output/analysis-report.md
  - recovered-evidence/analysis-output/stats-appendix.md
  - recovered-evidence/analysis-output/figure-catalog.md
linked_experiments:
  - ../codex-windowT8/START-M11.md
linked_results: []
---

# T8 / Round 11 / Ordinary-copy ablation / 2026-11-15

## 结论与决定

**M11已完成。普通按行搬运在Cora B1的8个预登记高N主格中，有6格耗时比ND2NZ降低25.35%–42.07%，满足至少5/8格降低20%的触发条件；结论是有条件优势。** FP16/N128两格反而慢30.50%–33.31%。普通按条在全部高N主格耗时约为ND的9.38–12.90倍。不能全局改成普通搬运，也不能将本回放称为完整SpMM。

普通按行后，六个获胜高N格的B0/B1加速比仍为1.480–1.488（B1耗时降低约32.4%–32.8%）。这支持保留重排减少总供数工作的价值；U/R/T一起变，不能声称只有降行数有效或段数不再有价值。合成实验的相对选路会随R翻转。

**FP32原始A列块的普通两stride拷贝链正确，但耗时为ND2NZ链的5.46–5.60倍。** 它解决了可行性问题，未支持性能替换；FP16普通链则约为ND链的0.17倍。M4的host预打包直装A是另一条路径。

全部45,920条正式计时已本地回收，并从每核原始时钟独立复算。计时前1,104项检查、计时后594项完整地址复核均PASS。实例已核对关机；新增使用约90分钟，按4元/小时估算约6元，以平台账单为准。没有新租实例，没有推送Git，没有修改原资料或论文论点。

## 实验身份与问题

来源分支codex-window，资料提交`f1a1c5e9d119fb1213dff509b5984b6145ee8c51`；隔离执行目录m11-execution，本地分支codex/m11。原8,975文件的SHA与40,865,920字节均复核，M4/M5统计和命令表复算PASS。既有M4没有通过Cora迁移的通用固定指令开销模型，M11不沿用旧耗时或假定固定t。

问题：在共同消费流水和合法布局下，三条B搬运路径如何取舍？普通路径是否改变重排价值？原始16×1列块A的FP32普通链能否正确且高效工作？本次round=11对应项目M11，不代表第11次独立重复实验。当前工作区未绑定Obsidian，本报告仅在本地落盘，未写回知识库。

## 设置、路径与执行口径

- 用户明确允许M8完成后重启复用OP08JZ85MYKCJKH3。M11只使用新目录`/data/t8-m11-20261115`；本次容器f295d978bae1，宿主dengjia-ascend910b-node02，物理NPU1、PCI0000:01:00.0，逻辑0。未操作旧M8目录/数据。
- 910B2 64GB、CANN9.0.0、aarch64、24 AIC/48 AIV、SDK L2=192MiB。完整环境在回收证据的environment目录。
- 阶段3：合成U64/R1,4,16,64与Cora B0/B1；FP16/FP32，N16/128/256，hot/cold，三路径；216点×20随机区组=4,320条。相同M4容量gmax控制，并非逐路径最优g。每点预热后测量，区组首尾同载荷各5次中位数漂移>5%则作废重跑；实际20/20接受、0作废。
- hot目标32MiB，cold目标1GiB唯一选中行，2GiB池；所有216配置CPU工作集审计PASS，cold实际工作集≥4×L2。保留Cora内部复用，不称每次访问都冷。实际池与唯一工作集在stage3-summary.csv分别报告。
- 阶段2：单核逐载荷同步，h1…16、N16/32/64/128/256、两精度、三路径与加载primitive，批量64/256/1024/4096；2,000点×20=40,000条。使用同一binary的host check模式和64MiB池，核内计时不变；外部哨兵覆盖完整区组。A两模式各40点×20=800条，共1,600条，在同一20个区组内随机交错，先后顺序10/10。A最大登记漂移4.523%，无作废。
- 正式总计45,920条。所有阶段保留原值和每核begin/end时钟，未按胜负/离群/拟合R²删点。
- 主判读事前锁定：Cora B1的N128/256×两精度×冷热=8格，严格多数5/8；N16是补充，不改分母。每格按普通两路径较小平均绝对耗时描述性选优；两条路径的全部配对区间分别保留。

路径与实际API次数：

| 路径 | 搬运方式 | 次数与限制 |
|---|---|---|
| p0 | ND2NZ | 按合法等长等间距段片合并；跨16行tile或stride*N>65535拆分 |
| p1 | 普通按行 | 每补齐行一次；blockCount=N/c0, blockLen=1, srcStride=0, dstStride=15 |
| p2 | 普通按特征条 | 有效tile段片数×N/c0；blockCount=h, blockLen=1, srcStride=N/c0−1, dstStride=0 |

c0=32/元素字节数，FP16为16、FP32为8，因此FP32按条是N/8。普通字段单位32B。三条B路径具有相同L1布局及后续转置加载；普通B没有新增一条转置。API次数不等于汇编/退休指令数。源码参数、固定上游提交与真实CANN9头文件见STAGE0.md、sdk-evidence及STRUCTURE.md。

计时覆盖MTE2/MTE1/MMAD/同步/Scalar的重叠区间，GetSystemCycle按50ticks/μs换算。以下阶段3的“μs/矩阵”是全卡makespan/(cycles×24)的吞吐归一化，**不是孤立单核矩阵延迟，也不是纯MTE2 busy**。

## 主结果与负结果

下表均为普通按行p1（8格选优均选p1）。均值±样本SD，20区组；比值=普通平均耗时/ND平均耗时；降时为1−比值，加速比为比值倒数。比值区间为成对bootstrap点95%CI。

{table(['B1主格', 'ND μs/矩阵', '按行 μs/矩阵', '耗时比', '95%CI', '时间下降', '加速比'], mainrows)}

六格的点区间上界也均低于0.8；但该结果未作两选一选择校正或同时区间保证。所有16个主对比的Holm符号检验p值、两条普通路径逐轮值、原始差值/效应量均在paired-contrasts.json。p2未隐藏：全部高N格耗时约为ND的9.38–12.90倍。

### N16补充，不计入主分母

{table(['B1补充格/路径', '普通/ND耗时比', '95%CI', '时间下降'], n16rows)}

本B1回放的描述性较优路径：FP16/N16按条，FP16/N128 ND，FP16/N256按行；FP32/N16 ND，FP32/N128/256按行。FP16/N16按行约等时；不要只凭统计p值宣称实用提升。该映射未在外部矩阵验证，不能成为通用选择器。

### 换路后重排仍值多少

Cora A0无对角，各170窗口：B0 ΣU=9583、ΣR=8565、T=681、补齐行10896；B1 ΣU=6035、ΣR=2927、T=455、补齐行7280。N128时B0/B1的ND API次数为4947/2481，按行为10896/7280，按条FP16为70256/25912、FP32为140512/51824。次数可解释实现结构，但不是单一性能机制证明。

{table(['按行配置', 'B0/B1加速比', '95%CI', 'B1时间下降'], rrows)}

普通按行在六个高N优势格仍有约1.48倍重排收益。减少U与补齐T可减少总工作，但本数据不能分离U/R/T的独立因果作用。

合成U64下，按行自身的高N R64/R1比接近1（本网格偏差至多约2.56%），但与ND的相对优势随R变化。hot的普通按行/ND耗时比如下，cold全值见图3/JSON：

{table(['精度', 'N', 'R1', 'R4', 'R16', 'R64'], synrows)}

因此“按行API数固定”不能推出“段数对最优供数决策不重要”：R≤16时这些hot格ND更快，R64时按行更快。段片合并、字节/地址与缓存等因素仍共同存在；没有PMU因果归因。

### 原始A列块加载链

两种链输入同一原始16×1列块，而不是混用M4预打包A。ND链为搬运+转置；普通FP16为连续搬运+转置，普通FP32为两条stride32B块搬运+转置。下表为同步整链每次有效代价k，单位μs；不是纯一条DMA延迟。

{table(['A链配置', 'ND k', '普通 k', '普通/ND', '95%CI'], arows)}

FP16普通链约快5.8倍；FP32普通链耗时约为ND的5.5倍。FP32正确可行，但当前实现不支持性能替换，也不证明其他普通布局不可能更好。M4的GM预打包L0A直装（FP32 repeatTimes=2、HF32关闭）不能当作本原始列块链的先验证据。

### 单核搬运与加载代价

代表性h16结果，单位μs/完整载荷（各k为20区组斜率均值）。全部h1…16与N32/64的均值、SD、CI和原始拟合保留在micro-fits.json、micro-per-block-fits.json。

{table(['精度', 'N', 'plain load', 'transpose load', 'ND copy', 'row copy', 'stripe copy'], mrows)}

各区组四批量拟合T=c+k×batch。520条20区组平均曲线的R²最小为{qmin:.9f}；逐区组R²最小为{bmin:.7f}，有{lowfits}个逻辑配置的平均逐区组R²低于0.999。两种R²不是同一统计量，全部保留、未剔除点。所有平均斜率为正。

h改变同时改变字节与API数；同h的三路径是同字节不同描述符/布局操作对照，仍不能识别一个通用固定指令t。plain与transpose primitive的输入解释不同，不能把差价简单加到可行端到端路径。阶段3所有B路径本就有同一转置加载。

## 统计验证

独立分析单位是20个随机时间区组，窗口/核不是独立样本。每配置报告均值、样本SD、t(19)点95%CI；主效果用平均绝对耗时之比（ratio of means）。其区间为10,000次成对区组bootstrap（seed20261115）。区组比值的均值/SD/tCI另存，不能与ratio of means混用。

符号检验为主，针对配对方向检验，不等于直接检验20%阈值；B1主族16比较作Holm校正，全144个探索对比另校正。本次16个主对比的Holm符号检验p均为0.0000305176；该检验回答方向差异，不回答20%阈值。16项log比中7项Shapiro在0.05下拒绝正态，支持保留非参数主检验。主族lag1相关范围约−0.306至0.239，仍不足以证明区组独立。配对log t、Wilcoxon与lag1只作假设/敏感性记录。小p值不证明时变独立或跨矩阵泛化。连续时间区组依赖、两路径选优与点区间多重性限制均保留，详见stats-appendix.md。

## 图表逐项解释

1. 图1分别画按行与按条对ND的比值，两个面板纵轴不同；六格优势、FP16/N128负结果和按条高代价同时可见。它支持条件选路，不支持全局替换。
2. 图2分精度/路径画B0/B1；各面板共同尺度，按行高N仍约1.48倍。它支持继续保留重排收益证据，不能归因于纯R。
3. 图3固定U64画按行/ND随R变化，路径偏好翻转。它阻止“按行次数固定，所以段数无价值”的过强解释。

图的源表、CI含义、图注与检查清单在figure-catalog.md。PNG/PDF位于analysis-output/figures；用户可只用MD表格和JSON复核，无需从图中读数。

## 正确性、错误记录与限制

- 计时前：主B198、原始A ND198、原始A普通198、micro510，共1,104项PASS。保存完整实际C/独立CPU参考、GM保护区、输入不变检查及执行文件哈希。范围为有限精确整数标记，不是任意NaN/负零等位语义。
- 原标记A按mod7、B按mod251重复，存在部分置换盲点。计时后补594项强地址复核：满秩非对称循环置换A，B前11特征编码33bit源行，每tile独立输出；三种A链各198项。全部PASS，同kernel、正式t8_micro哈希未改。不能把这594项写成计时前已执行。
- 首编译不支持HardEvent::MTE1_S，失败源码/日志保留，改为MTE1_M→M_S间接等待并重过全部门；Linux std::min<uint64_t>兼容修复同记录。大包上传413后使用102,824B源码包重建；下载受浏览器拦截后使用既有Jupyter授权文件接口，回传全部哈希一致。临时认证文件已删除。
- 运行中没有正确性失败、漂移作废或计时重试；失败目录仍保留编译故障，未伪称全程零错误。
- 只有Cora与本合成网格；真实B窗口配固定稠密A消费，非完整稀疏SpMM。共享gmax没有逐路径优化，不称最优实现或任意矩阵的最优路径。没有PMU证据证明具体瓶颈。
- 原始manifest的source_span_rows描述多16行；实际config[12]、工作集审计、CSV与核地址都用正确步长，测量未受影响。归档原件不改，metadata-corrections.json列每项，未来prepare.py仅修描述字段，1,530个输入binary逐字节未变。
- micro CSV working_set_bytes是通用副本容量记账，不是微载荷实际访问量；micro访问量h*N*元素字节（A为256*元素字节）。阶段3 api_calls只计B DataCopy；A micro同名字段计整链迭代，不能当内部API总数。派生表给出明确单位。
- 阶段3哨兵保留前后5次中位数与漂移，未保留5条单值；20轮主样本齐全。阶段2/A外部哨兵保留全部5条原值。登记细节/证据限制不作隐去。

## 对原假设的影响

应削弱“统一ND2NZ就足够代表直接供数”的假设，保留精度/N/缓存/段结构条件；也应阻止“普通按行后段数彻底无关”及“FP32 A普通链自动高效”的扩展。M11没有识别通用固定t，不能把本次数值塞回旧M4模型充当已验证参数。论文motivation与冻结结构保持原样，后续论文取舍交用户。

## 产物与离线复现索引

以下路径均相对于本报告所在m11-work，原始证据和派生产物分开：

| 产物 | 路径 |
|---|---|
| 完整不可变设备归档 | m11-evidence-complete.tar.gz（518,508,328字节） |
| 归档SHA256 | 0278def60a7771753a6d7921418434a7794e77ff7c03581dc098be040a3694a9 |
| 回传清单与复核 | archive-receipt.json；recovered-evidence/LOCAL-RETURN-VERIFICATION.json |
| 原时钟全量复算 | recovered-evidence/LOCAL-CLOCK-VERIFICATION.json；verify_raw_clocks.py |
| 原始逐轮/输出/时钟 | recovered-evidence/results-stage3-a0、results-stage2-a0、results-a-micro-a1/a2、results-A-paired |
| 正确性 | recovered-evidence/GATES-PASSED.json、STRONG-ADDRESS-GATES.json及gate-*目录 |
| 源码与环境 | src/与recovered-evidence/src/、recovered-evidence/environment/、build及失败日志 |
| 核对与协议 | STAGE0.md、STRUCTURE.md、PROTOCOL.md、sdk-evidence/、upstream-sources/ |
| 分析主表 | recovered-evidence/analysis-output/stage3-summary.csv、paired-contrasts.json、decision.json |
| 支持分析 | reordering-ratios.json、R-sensitivity.json、micro-fits.json、micro-mean-curve-quality.json、A-chain-paired-contrasts.json（均在analysis-output） |
| 分析与报告源码 | analyze.py、finalize_analysis.py；本报告由后者从已验证统计生成 |
| 元数据注释 | metadata-corrections.json、metadata-only-correction.patch、remote-source-reconciliation.json |
| 关机与费用 | shutdown-verification.json、environment-end-npu-smi.txt |

204,632个归档成员（含204,631文件的SHA清单）已安全解包逐项校验PASS，没有运行回传二进制。全部M11证据已本地落地，无远端独有的必要产物；不要依赖关机后约36小时的远端保留期。关机UI状态“已关机”在上海2026-11-15 19:18复核，结束NPU无进程；平台累计7h27m→8h57m，增量约90分钟/6元，非精确账单。

离线重算（使用本机NumPy/SciPy/Matplotlib；不启动实例、不执行回传binary）：

```sh
cd /Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work
M11_DATA_ROOT="$PWD/recovered-evidence" python3 analyze.py
```

原设备归档内analyze.py保留当时版本；本地analyze.py在相同统计步骤后调用finalize_analysis.py，增补报告/图表与R²口径，未改原测量数据。再次复算会覆盖本地analysis-output与本报告；原tar不受影响。

## 后续操作决定

M11设备阶段结束，保持实例关闭。现有证据支持保留按行/按条/ND三候选的条件性比较，暂不统一替换B路径；FP32原始A保持已验收ND链作为性能参照。若用户继续研究，优先验证独立矩阵的真实稀疏端到端消费与逐路径g调优，再决定是否需要改论文；这些是建议，不在本次自动新增实验范围。
'''
    name = '2026-11-15--t8--r11--ordinary-copy-ablation.md'
    (work / name).write_text(report)
    print(json.dumps({'report': str(work/name), 'figures': 3, 'mean_curve_r2_min': qmin, 'per_block_r2_min': bmin}, indent=2))


if __name__ == '__main__':
    finalize(Path(os.environ.get('M11_DATA_ROOT', str(Path(__file__).resolve().parent / 'recovered-evidence'))))
