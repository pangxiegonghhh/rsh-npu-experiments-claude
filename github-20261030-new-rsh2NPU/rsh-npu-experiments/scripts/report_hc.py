"""Create a readable Chinese H-C report from the independent local audit."""
from __future__ import annotations

from pathlib import Path
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    dest = ROOT/'results/hc'
    x = json.loads((dest/'local_audit.json').read_text())
    assert x['passed'] and x['version'] == 'H-C' and x['stop_required']
    lines = ['# H-C：固定分流，动态尾补零交给Cube', '',
             'H-C已完成并停止，主版本5/6。H-Skip尚未启动，必须等用户明确继续。', '',
             '沿用V2实测排列与H-V默认4/2的G/S/T/Z，不重新排序或分流。G仍走Cube，S仍走AIV；将动态尾T补到16行后交给Cube，保持整行归属和完整原行序输出，不拆长行。八矩阵采用真实稀疏结构与原有固定有符号FP16数值。', '',
             f"{x['smoke_checks']}个设备小例检查、24配置×3独立进程、9个H-C/H-C空对照全部数值正确；H-C最大绝对误差{x['hc_max_abs_error']:.8g}。", '',
             f"配对比的24配置几何平均：H-V/H-C **{x['hv_over_hc_geomean']:.6f}**，V2/H-C **{x['v2_over_hc_geomean']:.6f}**，V0/H-C **{x['v0_over_hc_geomean']:.6f}**。比值>1表示H-C更快。", '']
    for key, name in [('hv', 'H-V'), ('v2', 'V2'), ('v0', 'V0')]:
        faster, slower = x[key+'_all_three_faster'], x[key+'_all_three_slower']
        lines.append(f"相对{name}：{faster}配置三进程均快，{slower}配置均慢，{24-faster-slower}配置方向混合；{x[key+'_gain_above_null_envelope']}配置在三个进程均超过空对照逐次比p95。")
    lines += ['', f"H-C/H-C空对照逐次配对比5%–95%为{x['null_ratio_p05_p95'][0]:.6f}–{x['null_ratio_p05_p95'][1]:.6f}；九个进程的中位配对比范围{x['null_process_median_range'][0]:.6f}–{x['null_process_median_range'][1]:.6f}。进程噪声保护值max(1,九个进程中位比及其倒数)为{x['null_process_noise_guard']:.6f}。这些均为描述性诊断，不能充当显著性检验。", '',
              '## 完整驻留调用', '',
              '每版本10次预热、30个样本，3个独立进程。V0/V2/H-V/H-C在同一进程内逐轮随机交错，种子20261018+进程编号，B轮换2份。计时包括输出/打包区清零、B行收集、混合计算、原行序恢复和设备同步；CPU预处理与首次H2D不计入。四版本共享相同A/B/golden，当前每版本2160正式样本。', '',
              '时间为三个进程中位数的中位数，括号为合并90样本IQR；配对比先逐轮相除，再取进程内中位数及三个进程中位数，不保证等于表中时间直接相除。', '',
              '| 矩阵 | N | V0 μs (IQR) | V2 μs (IQR) | H-V μs (IQR) | H-C μs (IQR) | H-V/H-C | V2/H-C | V0/H-C |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in x['rows']:
        cells = [f"{row[key+'_median_us']:.3f} ({row[key+'_iqr_us']:.3f})" for key in ['v0', 'v2', 'hv', 'hc']]
        lines.append(f"| {row['matrix']} | {row['n']} | "+' | '.join(cells)+
                     f" | {row['hv_over_hc']:.3f} | {row['v2_over_hc']:.3f} | {row['v0_over_hc']:.3f} |")
    lines += ['', 'H-V/H-C比较相同分流下改变尾部执行路径后的总体影响。两者的AIV工作量、Cube块数、B收集与任务分配共同变化，差值不能称为纯尾部计算成本。V0/V2是相同后端的机制对照；本轮没有Neutron或强库实装对照。不能直接混用H-V上轮的绝对时间，以上H-V是本轮四版本配对的新测量。', '',
              '## 冻结结构与尾部额外工作', '',
              'G/S/T/Z的原始行号、分组和阈值逐字节继承H-V默认计划，唯一覆盖全部原始行和非零。Z指分流扫描单独跳过的零首行；G/T内部零行仍在原组，不重复统计。T是分流后的动态尾，可能由逐行移到S而产生，不等于M模W。', '',
              '| 矩阵 | G行/NNZ% | S行/NNZ% | T行/NNZ% | Z行 | Cube组 H-V→H-C | k16块 H-V→H-C | AIV行 H-V→H-C |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in x['structure']:
        cells = [f"{s[key]['rows']}/{s[key]['nnz']/s['nnz']*100:.3f}%" if s['nnz'] else f"{s[key]['rows']}/0.000%" for key in ['G', 'S', 'T']]
        lines.append('| '+s['matrix']+' | '+' | '.join(cells)+
                     f" | {s['Z']['rows']} | {s['hv_cube_groups']}→{s['cube_groups']} | {s['hv_k16_tiles']}→{s['k16_tiles']} | {s['hv_aiv_rows']}→{s['aiv_rows']} |")
    lines += ['', '| 矩阵 | T真实行 | 补零行 | T额外k16块 | T物理槽 | 额外B收集行/调用 | H-C布局秒 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for s in x['structure']:
        lines.append(f"| {s['matrix']} | {s['T']['rows']} | {s['tail_padding_rows']} | {s['tail_k16_tiles']} | {s['tail_added_physical_slots']} | {s['tail_b_gather_rows_per_call']} | {s.get('layout_seconds', 0):.6f} |")
    lines += ['', 'T补到16行对应的rowmap以-1屏蔽补齐行输出；补齐列引用零哨兵B行。T全零时可产生零k16块的尾组，仍单独验证行映射、清零与完整输出。上述额外B行数是布局收集槽数，包含补齐槽，不能当作独立全局内存流量测量。', '',
              '## 阈值处理与事前规则', '',
              'H-C设备测量前保存prospective_threshold_rule.json并在manifest冻结哈希。三个开发矩阵ca-HepTh、email-Enron、bcsstk17，固定N64；每进程对三个矩阵的H-V/H-C配对比作几何平均。只有三进程均严格超过本轮H-C空对照进程噪声保护值，才满足切换H-C策略的条件；还需默认H-C未稳定超过最强受控完整输出基线或存在实测负载/补零问题，才触发H-C单独网格。', '',
              '三进程开发集H-V/H-C聚合配对比：'+', '.join(f'{t:.6f}' for t in x['development_hv_over_hc_per_process'])+'。',
              f"均超过本轮进程噪声保护值：{'是' if x['development_strategy_switch_above_null_guard'] else '否'}。", '',
              '本轮明确决策记录：', '', '```json', json.dumps(x['threshold_decision'], ensure_ascii=False, indent=2), '```', '',
              'H-V历史选择规则和结论保持原样：默认4/2、8/4约11%的探索性信号，未追溯改判。H-C/H-V本轮主对照继续使用原默认G/S/T/Z。即使有单独候选补测，也必须与本表默认结果分开记录。', '',
              '## 首次调用、准备成本与限制', '',
              '以下单位为微秒，取三个进程中位数。初始设备准备不包含在正式驻留调用计时里。CPU重排与分流沿用既有V2/H-V结果，本轮只构建H-C布局；完整主机准备、q次复用摊销、分项峰值workspace和相对L2尚未测完。', '',
              '| 矩阵 | N | H-C首次调用 μs | 初始设备准备 μs |',
              '|---|---:|---:|---:|']
    for row in x['rows']:
        xs = [json.loads((dest/'measurements'/row['matrix']/f'N{row["n"]}'/f'run{rep}.json').read_text()) for rep in range(3)]
        lines.append(f"| {row['matrix']} | {row['n']} | {statistics.median(y['records'][3]['first_us'] for y in xs):.3f} | {statistics.median(y['records'][3]['device_prepare_us'] for y in xs):.3f} |")
    lines += ['', '未修改原混合程序，SHA256与H-V一致，复用H-V独立msprof证据：原生MIX_AIC_1_2，24 AIC/48 AIV且两条流水均有实际活动。本轮H-C新布局通过设备小例和完整输出检查，未重新采集profile，精确逐核重叠比例仍未知。正式时间未附加性能采集开销；原程序JSON中的not_yet_profiled是冻结标签，以单独验证文件为准。', '',
              '## 波动标记', '', '任一版本的三个进程中位数max/min>1.10：', '']
    for flag in x['timing_flags']:
        cells = [f"{name} {flag[key]:.3f}" for key, name in [('v0', 'V0'), ('v2', 'V2'), ('hv', 'H-V'), ('hc', 'H-C')]]
        lines.append(f"- {flag['matrix']}/N{flag['n']}："+'，'.join(cells)+'。')
    if not x['timing_flags']:
        lines.append('无。')
    lines += ['', '全部原始样本保留，未删除慢点或选择有利进程。证据包括manifest/progress、预声明阈值规则、smoke、measurements、null_control、冻结plans、case_manifest和源码快照。audit_hc.py从原始样本重算统计，并在不依赖GB级案例二进制的紧凑恢复包中验证结构与哈希；完整二进制及CPU恢复脚本另外保存。', '']
    (dest/'分析.md').write_text('\n'.join(lines))
    print(dest/'分析.md')


if __name__ == '__main__':
    main()
