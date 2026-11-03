"""Render a Chinese H-Skip report, keeping same-R and optimistic ratios separate."""
from __future__ import annotations
from pathlib import Path
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    dest = ROOT/'results/skip'
    x = json.loads((dest/'local_audit.json').read_text())
    assert x['passed'] and x['version'] == 'H-Skip' and x['next_version'] == 'none' and x['stop_required']
    lines = ['# H-Skip：固定结构，排除动态尾窗的主体诊断', '',
        'H-Skip已完成并停止，六个主版本6/6。本轮授权到此结束，没有自动进入新的实验。阶段完成不等于完整框架的端到端收益已经验收。', '',
        '固定W16、阈值4/2，复用V2实测排列和H-V默认G/S/T/Z。H-Skip保留原G走Cube、原S走AIV，仅不执行T；R=原始行全集去掉T，Z仍属于R，零输出按原规则处理。R通常不连续，不能把它当作前缀。V0-R只计算相同R；V2-R将已有V2排列限制到R后重新按固定W窗口布局，不重跑相似度排序。三者使用完整A列空间和同一完整B/golden，未按T行号删除B行。', '',
        f"{x['smoke_cases']}个CPU布局、{x['smoke_checks']}个设备小例进程（{x['smoke_variant_checks']}次版本检查）、24配置×3独立进程、9个H-Skip/H-Skip空对照全部通过；H-Skip保留行最大绝对误差{x['skip_max_abs_error']:.8g}。", '',
        f"空R小例共有{x['empty_r_smoke_processes']}个设备进程，只验证调度安全、空工作与空范围校验，不作为非空数值正确性的证据。正式24配置的R均非空。", '',
        '## 相同输出R的比较', '',
        '以下比较仅涉及相同保留行，都是部分输出诊断。比值>1表示H-Skip更快。不能将这些结果称为完整SpMM的加速。', '']
    for key, name in [('v0r', 'V0-R'), ('v2r', 'V2-R')]:
        stat = x['same_r'][key+'_over_skip']
        faster, slower = stat['all_three_faster'], stat['all_three_slower']
        lines.append(f"{name}/H-Skip的24配置几何平均 **{stat['geomean']:.6f}×**；{faster}配置三进程均快，{slower}均慢，{24-faster-slower}方向混合；{stat['gain_above_null_envelope']}配置在三个进程均超过空对照逐次配对比p95。")
    lines += ['', '每版本10次预热、30个样本、3个独立进程，种子20261018+进程编号。七个版本V0/V2/H-V/H-C/V0-R/V2-R/H-Skip在同一进程内逐轮随机交错，轮换两份B；每版本2160正式样本，共15120个正式样本。', '',
        '计时是完整同步驻留调用，包括输出/打包区清零、B行收集、混合计算、原行序恢复和设备同步，CPU预处理与首次H2D不计入。所有R版本仍分配并清零完整M行输出；Cube结果仅遍历已布局group槽并按rowmap恢复到原始行号，AIV直接写保留行。此实现没有把输出缓冲压缩成|R|行。因此它用于现有后端的受控主体比较，不是部分输出算子的最优实现。', '',
        '时间为三个进程中位数的中位数，括号为合并90样本IQR。配对比先逐轮相除，再取进程内中位数及三个进程中位数；不保证等于表中时间直接相除。', '',
        '| 矩阵 | N | R/M | V0-R μs (IQR) | V2-R μs (IQR) | H-Skip μs (IQR) | V0-R/H-Skip | V2-R/H-Skip |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for row in x['rows']:
        cells = [f"{row[key+'_median_us']:.3f} ({row[key+'_iqr_us']:.3f})" for key in ['v0r', 'v2r', 'skip']]
        lines.append(f"| {row['matrix']} | {row['n']} | {row['valid_rows']}/{row['m']} | "+' | '.join(cells)+
                     f" | {row['v0r_over_skip']:.3f} | {row['v2r_over_skip']:.3f} |")
    lines += ['', '## 完整参考除以H-Skip的乐观比', '',
        '下表的分子计算完整输出，分母只计算R，工作集合不同。这是忽略尾部执行成本后的乐观诊断，不能称为同输出加速，也不是完整框架可达到的严格数学上界。删除T会改变AIV负载、调度和缓存，H-C还改变Cube块与B收集，不能把时间差当作纯尾部成本。', '']
    for key, name in [('v0', 'V0'), ('v2', 'V2'), ('hv', 'H-V'), ('hc', 'H-C')]:
        lines.append(f"{name}/H-Skip的24配置乐观比几何平均：{x['optimistic_full'][key+'_over_skip']['geomean']:.6f}。")
    lines += ['', '| 矩阵 | N | V0 μs | V2 μs | H-V μs | H-C μs | V0/H-Skip | V2/H-Skip | H-V/H-Skip | H-C/H-Skip |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in x['rows']:
        cells = [f"{row[key+'_median_us']:.3f}" for key in ['v0', 'v2', 'hv', 'hc']]
        ratios = [f"{row[key+'_over_skip']:.3f}" for key in ['v0', 'v2', 'hv', 'hc']]
        lines.append(f"| {row['matrix']} | {row['n']} | "+' | '.join(cells+ratios)+' |')
    lines += ['', '本表完整版本在本轮重新同设备配对测量；不直接拿前轮绝对时间计算比值。相同R结果与乐观结果分别存放于local_audit.json的same_r和optimistic_full，没有混入前五个完整主版本的几何平均。', '',
        '## 被排除的动态尾与主体结构', '',
        'T是分流后留下的动态尾，可能因逐行送入S而产生，不等于M模W。保留每条T和R的原始行号、限制后的V2行序、完整冻结routing.json与valid掩码。T为空时三部分输出方案按等价完整覆盖标注；本轮八个正式矩阵T均非空。', '',
        '| 矩阵 | M | R行 | R NNZ | T行 | T行% | T NNZ | T NNZ% | G行 | S行 | Z行 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in x['structure']:
        lines.append(f"| {s['matrix']} | {s['m']} | {s['R']['rows']} | {s['R']['nnz']} | {s['T']['rows']} | {s['tail_row_fraction']*100:.6f} | {s['T']['nnz']} | {s['tail_nnz_fraction']*100:.6f} | {s['G']['rows']} | {s['S']['rows']} | {s['Z']['rows']} |")
    lines += ['', '| 矩阵 | V0-R AIV行 | V2-R组/k16块 | H-Skip组/k16块 | H-Skip AIV行 | 布局秒 |',
        '|---|---:|---:|---:|---:|---:|']
    for s in x['structure']:
        v = s['variants']
        lines.append(f"| {s['matrix']} | {v['V0-R']['aiv_rows']} | {v['V2-R']['cube_groups']}/{v['V2-R']['k16_tiles']} | {v['H-Skip']['cube_groups']}/{v['H-Skip']['k16_tiles']} | {v['H-Skip']['aiv_rows']} | {s['layout_seconds']:.6f} |")
    lines += ['', 'H-Skip的Cube组、colref、tiles、rowmap与H-V逐字节相同，srows严格等于冻结S，valid仅屏蔽T。V2-R限制的是输出行排列，不改变A的列空间；即使保留行访问与T相同编号的B行，也必须正确取数，已由非连续R小例覆盖。未拆超长行。', '',
        '## 空对照与波动', '',
        f"H-Skip/H-Skip逐次配对比5%–95%：{x['null_ratio_p05_p95'][0]:.6f}–{x['null_ratio_p05_p95'][1]:.6f}；九个进程中位配对比范围{x['null_process_median_range'][0]:.6f}–{x['null_process_median_range'][1]:.6f}；进程噪声保护值{x['null_process_noise_guard']:.6f}。它们是描述性噪声诊断，不是显著性检验。", '',
        '任一版本三个进程中位数max/min>1.10的配置：', '']
    for flag in x['timing_flags']:
        cells = [f"{name} {flag[key]:.3f}" for key, name in zip(['v0','v2','hv','hc','v0r','v2r','skip'], ['V0','V2','H-V','H-C','V0-R','V2-R','H-Skip'])]
        lines.append(f"- {flag['matrix']}/N{flag['n']}："+'，'.join(cells)+'。')
    if not x['timing_flags']:
        lines.append('无。')
    lines += ['', '全部样本和慢点原样保留，没有删点或选择有利进程。H-Skip禁止阈值调优；默认4/2、H-V历史8/4探索信号及HC决策保持不变，没有用部分输出结果追溯改判。', '',
        '## 首次调用与尚未完成的判断', '',
        '以下单位为微秒，取三个进程的中位数。初始设备准备不包含在正式驻留调用中。', '',
        '| 矩阵 | N | H-Skip首次调用 μs | 初始设备准备 μs |',
        '|---|---:|---:|---:|']
    for row in x['rows']:
        records = [json.loads((dest/'measurements'/row['matrix']/f'N{row["n"]}'/f'run{rep}.json').read_text())['records'][-1] for rep in range(3)]
        lines.append(f"| {row['matrix']} | {row['n']} | {statistics.median(r['first_us'] for r in records):.3f} | {statistics.median(r['device_prepare_us'] for r in records):.3f} |")
    lines += ['', '原程序SHA256与H-V/HC一致，复用H-V独立profile验证：MIX_AIC_1_2，24AIC/48AIV且两条流水实际活动；本轮新布局有独立数值检查，没有重新采profile，精确逐核重叠比例仍未知。冻结JSON标签not_yet_profiled以独立验证文件解释。', '',
        '六主版本完成仅表示本轮受控实验阶段结束。CPU预处理、首次H2D、q次复用摊销、相对L2与分项峰值workspace，以及Neutron/强库同设备基线仍需另行设计与授权；不能据此宣称完整端到端加速或论文创新已经成立。', '',
        '证据包括manifest/progress、七路原始样本、空对照、设备小例、smoke输入CSR、冻结plans、case_manifest与源码快照。audit_skip.py在紧凑恢复包中从原始CSR、实测V2排列及冻结G/S/T重建计划哈希，单独核对R掩码、T行号、S保留与A/B/golden一致；完整case二进制另存并可按测量哈希恢复。', '']
    (dest/'分析.md').write_text('\n'.join(lines))
    print(dest/'分析.md')


if __name__ == '__main__':
    main()
