"""Readable H-V results from independently audited records; no device runs."""
from pathlib import Path
import json,statistics
ROOT=Path(__file__).resolve().parents[1]
def main()->None:
    d=ROOT/'results/hv';x=json.loads((d/'local_audit.json').read_text());assert x['passed']
    lines=['# H-V：RSH滑窗分流，尾行走AIV','','H-V已完成并停止，下一主版本H-C等待用户明确继续。复用V2实测行排列，W16、默认阈值4/2，整行归属、不拆长行；G走Cube，S与动态尾T走AIV，输出完整。八矩阵沿用真实稀疏结构和固定有符号FP16测试数值。','',f"26设备小例、24配置×3独立进程、9个H-V/H-V空对照全部正确；最大绝对误差{x['hv_max_abs_error']:.8g}。",'',f"V2/H-V配对比几何平均{x['v2_over_hv_geomean']:.6f}；V0/H-V为{x['v0_over_hv_geomean']:.6f}。比值>1代表H-V更快。相对V2：{x['v2_all_three_faster']}点三进程均快、{x['v2_all_three_slower']}点均慢，{24-x['v2_all_three_faster']-x['v2_all_three_slower']}点方向混合；{x['v2_gain_above_null_envelope']}点全部进程超过空对照逐次比95%上界。",'',f"空对照逐次比5%–95%范围{x['null_ratio_p05_p95'][0]:.6f}–{x['null_ratio_p05_p95'][1]:.6f}；进程中位比范围{x['null_process_median_range'][0]:.6f}–{x['null_process_median_range'][1]:.6f}。这些是描述性噪声诊断，不是显著性检验，接近1的小幅差异不直接宣称稳定收益。",'',
    '## 完整驻留调用','','每版本10预热、30样本、3进程。V0/V2/H-V每轮按固定种子随机交错；计时含清零、B行收集、原生混合任务、原行序恢复和同步，CPU预处理和初始H2D不计入。表中微秒时间为三进程中位数之中位数，括号为合并90样本IQR；配对比先每轮求比、进程内中位、再三进程中位，因此不一定等于表中时间直接相除。','','| 矩阵 | N | V0 μs (IQR) | V2 μs (IQR) | H-V μs (IQR) | V2/H-V | V0/H-V |','|---|---:|---:|---:|---:|---:|---:|']
    for r in x['rows']:
        cells=[f"{r[v+'_median_us']:.3f} ({r[v+'_iqr_us']:.3f})" for v in ['v0','v2','hv']];lines.append(f"| {r['matrix']} | {r['n']} | "+' | '.join(cells)+f" | {r['v2_over_hv']:.3f} | {r['v0_over_hv']:.3f} |")
    lines+=['','V0/V2均为相同设备、相同程序的机制对照；当前没有Neutron或强库对照，不据此声称超越论文实现。H-V相对V2包含分流、滑动成窗、空行处理与混合执行变化的联合影响。','',
    '## 结构分流','','G/S/T/Z行数唯一划分全部原始行；Z仅指扫描时单独跳过的零首行，G/T内部的零行仍留在其原归属，不重复统计。G是完整16行窗口，S是非尾残余，T是动态尾。','','| 矩阵 | G行/NNZ% | S行/NNZ% | T行/NNZ% | Z行 | G内零行 | Cube块 V2→H-V | 分流秒 | 布局秒 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in x['structure']:
        cells=[f"{s[v]['rows']}/{s[v]['nnz']/s['nnz']*100:.3f}%" for v in ['G','S','T']];lines.append('| '+s['matrix']+' | '+' | '.join(cells)+f" | {s['Z']['rows']} | {s['G']['zero_rows']} | {s['v2_k16_tiles']}→{s['k16_tiles']} | {s['partition_seconds']:.4f} | {s['layout_seconds']:.4f} |")
    lines+=['','全部实际G/S/T原行号保存在plans/*/routing.json，供H-C/H-Skip复用。各N的CSR/B/golden哈希与V0/V2一致。结构统计还保存列并集分位数、补齐槽数、B收集行数和计划字节数，见structure.json。沿用V2的近似共享列候选排序，未重排选择更有利结果。','',
    '## 混合执行证据','','独立msprof诊断使用含Cube和AIV任务的动态尾小例，完整数值正确。五次rsh_mix调用都被设备识别为MIX_AIC，24个AIC块与48个AIV块；每次均有非零AIC MAC和AIV Vector活动。结果支持原生混合任务实际执行了两路工作，未用先Cube再AIV的串行替代。精确的逐核时间重叠比例尚未分解。采集时间不混入正式性能样本。原始CSV、时间线和二进制采集数据全保存在profile/。原程序JSON中not_yet_profiled标签是冻结字符串；以mixed_validation.json及原始报告为实际验收依据。','',
    '## 条件性阈值补测','']
    gd=x['threshold_decision']
    if gd.get('grid_complete'):
        gs=json.loads((d/'grid/summary.json').read_text());lines+=[f"默认完整版本在部分配置未超过最强受控对照，按计划在三开发矩阵N={gs['n']}做九阈值网格；默认3配置复用，新增24配置×3进程，四版本V0/V2/默认H-V/候选H-V配对，全部数值正确。默认G/S/T与主结果未覆盖。",'', '| tau_nnz | tau_inc | 三矩阵聚合延迟 μs | 三进程默认/候选聚合配对比 |','|---:|---:|---:|---|']
        for r in gs['options']:lines.append(f"| {r['tau_nnz']} | {r['tau_inc']} | {r['aggregate_latency_us']:.3f} | "+', '.join(f'{v:.4f}' for v in r['paired_default_over_candidate_per_process'])+' |')
        b=gs['lowest_measured_latency'];s=gs['selected_public_configuration'];lines+=['',f"已测聚合延迟最低为({b['tau_nnz']},{b['tau_inc']})，但公开采用配置为({s['tau_nnz']},{s['tau_inc']})。只有三进程开发集聚合配对改善都超过空对照描述性p95={gs['selection_noise_limit']:.6f}才改默认；该规则是保守探索性保护，不是显著性检验。",'本轮保留默认，其余五矩阵沿用已完成的默认评估。候选(8,4)的三次一致改善作为探索性信号保留，未做该候选的五矩阵冻结评估。全局逐次噪声上界用于聚合改善的门槛较保守，不据此否认候选信号。' if gs['default_retained'] else '公共阈值改变，需单列其余五矩阵的冻结后评估。']
    lines+=['','## 首次调用与初始设备准备','','单位微秒。CPU重排成本沿用V2的2.736–156.385秒区间，分流/布局新增耗时见上表；仍未覆盖完整主机准备流水线，暂不报告完整q次复用端到端收益。现有设备runner只记录最大绝对误差，没有导出相对L2；workspace可按配置估算，未做分项峰值采集。','','| 矩阵 | N | H-V首次调用 | 初始设备准备 |','|---|---:|---:|---:|']
    for r in x['rows']:
        xs=[json.loads((d/'measurements'/r['matrix']/f'N{r["n"]}'/f'run{i}.json').read_text()) for i in range(3)];lines.append(f"| {r['matrix']} | {r['n']} | {statistics.median(y['records'][2]['first_us'] for y in xs):.3f} | {statistics.median(y['records'][2]['device_prepare_us'] for y in xs):.3f} |")
    lines+=['','## 波动标记','','任一版本进程中位数max/min>1.10：','']
    for f in x['timing_flags']:lines.append(f"- {f['matrix']}/N{f['n']}：V0 {f['v0']:.3f}，V2 {f['v2']:.3f}，H-V {f['hv']:.3f}。")
    if not x['timing_flags']:lines.append('无。')
    lines+=['','全部原始样本保留，未删慢点。原始证据包括manifest/progress、smoke、measurements、null_control、plans、profile和grid；源码快照、案例二进制恢复哈希和本机紧凑恢复审计另存。','']
    (d/'分析.md').write_text('\n'.join(lines));print(d/'分析.md')
if __name__=='__main__':main()
