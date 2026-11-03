"""Generate readable V2 tables from audited raw results; no device execution."""
from pathlib import Path
import json,math,statistics
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def main():
    dest=ROOT/'results/v2';x=json.loads((dest/'local_audit.json').read_text());assert x['passed']
    lines=['# V2：重排后固定16行窗全Cube','',
    'V2已完成并停止；下一主版本为H-V，必须等用户继续。主比较为同进程V1/V2，次比较为V0/V2；比值大于1表示V2更快。', '',
    f"24配置、72三版本配对进程、9个V1/V1空对照、20组重排小例，均数值通过。V2最大绝对误差{x['v2_max_abs_error']:.8g}。",'',
    f"V1/V2配对比几何平均{x['v1_over_v2_geomean']:.6f}；V0/V2为{x['v0_over_v2_geomean']:.6f}。V1对照下{x['v1_all_three_faster']}点三进程均快、{x['v1_all_three_slower']}点均慢；{x['v1_gain_above_null_envelope']}点三进程比值均超过空对照逐次比95%分位。",'',
    f"空对照逐次比5%–95%范围{x['null_ratio_p05_p95'][0]:.6f}–{x['null_ratio_p05_p95'][1]:.6f}，空对照进程中位比范围{x['null_process_median_range'][0]:.6f}–{x['null_process_median_range'][1]:.6f}。这是描述性噪声诊断，不能视为显著性检验。",'',
    '## 同设备完整驻留调用','',
    '单位微秒。每列时间取三个独立进程的采样中位数之中位数，括号为合并90样本IQR；比值先对每轮配对求比、进程内取中位数、再取三进程中位数，因此不保证等于表中时间直接相除。', '',
    '| 矩阵 | N | V0 | V1 | V2 | V1/V2 | V0/V2 | V2首次调用 | V2设备准备 |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    pos=lines.index('## 同设备完整驻留调用')
    lines[pos:pos]=['重排收益主要集中在ns3Da；其他矩阵多接近持平，thermal1三个宽度均略慢。email-Enron/N256三个版本均出现约3倍进程跨度，根因尚未定位，完整样本与波动标记保留。几何平均收益不能视为普遍稳定提升。','']
    amort=[]
    for r in x['rows']:
        xs=[json.loads((dest/'measurements'/r['matrix']/f'N{r["n"]}'/f'run{i}.json').read_text()) for i in range(3)]
        first=statistics.median(z['records'][2]['first_us'] for z in xs)
        prep=statistics.median(z['records'][2]['device_prepare_us'] for z in xs)
        cells=[f"{r[v+'_median_us']:.3f} ({r[v+'_iqr_us']:.3f})" for v in ['v0','v1','v2']]
        lines.append(f"| {r['matrix']} | {r['n']} | "+' | '.join(cells)+f" | {r['v1_over_v2']:.3f} | {r['v0_over_v2']:.3f} | {first:.3f} | {prep:.3f} |")
    lines+=['','调用计时含清零、调用内B行收集、Cube、原行序恢复、同步；B原值已在设备。CPU排序/布局与主机到设备初始拷贝不在该计时内。首次调用、设备准备单列。V0/V1仅为同后端机制对照，未进行Neutron或强库比较。','','## 结构与预处理','','| 矩阵 | V1块数 | V2块数 | 块数下降 | 重排秒 | 布局秒 | V2有效密度 | 24核静态负载max/mean V1→V2 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    diag=[]
    for s in x['structure']:
        im=[];totals=[]
        for v in ['v1','v2']:
            p=ROOT/f'cases_{v}'/s['matrix']/f'N16/{v.upper()}/cube_ptr.bin';ptr=np.fromfile(p,np.int64);counts=np.diff(ptr)
            work=np.array([counts[c::24].sum() for c in range(24)])
            im.append(float(work.max()/max(1,work.mean())));totals.append(work.tolist())
        diag.append({'matrix':s['matrix'],'v1_aic_k16_work':totals[0],'v2_aic_k16_work':totals[1],'v1_max_mean':im[0],'v2_max_mean':im[1]})
        lines.append(f"| {s['matrix']} | {s['v1_k16_tiles']} | {s['k16_tiles']} | {(1-s['k16_tiles']/s['v1_k16_tiles'])*100:.2f}% | {s['seconds']:.3f} | {s['layout_seconds']:.3f} | {s['physical_density']*100:.2f}% | {im[0]:.3f}→{im[1]:.3f} |")
    lines+=['','每块16×16；有效密度=NNZ/(块数×256)，含填充。静态负载仅按当前g=core,core+24分配的K块数估算，不是设备profiler结论。重排是Python CPU实现，候选预算256、k16，有热门列采样、孤立节点尾放置；属于明确记录的近似迁移，不是原论文精确复现。段内two-opt仅改变本固定窗内顺序，不能单独解释块数减少。','','重排/布局仅报告实际测到的部分；不把不完整的CPU准备时间称为完整端到端耗时。图构造未做性能优化，后续需验证复用次数下的摊销；本轮不据此承诺应用端收益。','','## 波动与证据','','进程中位数最大/最小超过1.10的配置：']
    for f in x['timing_flags']:lines.append(f"- {f['matrix']}/N{f['n']}：V0 {f['v0']:.3f}、V1 {f['v1']:.3f}、V2 {f['v2']:.3f}。")
    if not x['timing_flags']:lines.append('无。')
    lines+=['','原始证据：manifest.json、progress.json、measurements/、null_control/、smoke/、orders/*/order.bin及structure.json、source_snapshot/。所有原始样本保留，不剔除慢点。没有为了改善数字而临时选择重排/阈值或修改内核。','']
    (dest/'分析.md').write_text('\n'.join(lines));(dest/'structure_diagnostics.json').write_text(json.dumps(diag,indent=2));print(dest/'分析.md')
if __name__=='__main__':main()
