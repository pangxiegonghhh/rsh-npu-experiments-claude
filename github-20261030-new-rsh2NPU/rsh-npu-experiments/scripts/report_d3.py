"""D3 saved-data reports, rigorous descriptive bundle and actual figures; no device work."""
from pathlib import Path
import math,statistics,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));D=ROOT/'results/d3'
from scripts.prepare_d3 import read,save,sha
PRIMARY=['L/F','F/J','L/J'];ALT={'L/F':'L-B/F-B','F/J':'F-B/J-B','L/J':'L-B/J-B'}
def main():
    x=read(D/'analysis.json');audit=read(D/'independent_audit.json');assert x['passed'] and audit['passed'];rows=x['rows'];out=D/'figures';out.mkdir(exist_ok=True);names=[r['matrix'].split('_',1)[-1]+f" / {r['n']}" for r in rows];y=np.arange(len(rows));fig,axes=plt.subplots(1,3,figsize=(13,10),sharey=True,layout='constrained')
    for ax,key in zip(axes,PRIMARY):
        for i,r in enumerate(rows):
            c=r['contrasts'][key];g=c['geomean'];ci=c['bootstrap95_conditional'];same=c['identical_execution'];color='#888888' if same else '#267f9b';ax.errorbar(g,i,xerr=[[g-ci[0]],[ci[1]-g]],fmt='o',mfc='white' if same else color,color=color,capsize=2,markersize=4);ax.scatter(r['contrasts'][ALT[key]]['geomean'],i+.12,marker='x',color='#b67b38',s=16)
        ax.axvline(1,color='gray',ls='--',lw=1);ax.set_title(key);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Full-call time ratio');ax.set_yticks(y,names)
    axes[0].invert_yaxis();fig.suptitle('D3: fixed workflows, full output, common native backend');fig.legend(handles=[Line2D([0],[0],marker='o',color='#267f9b',ls='',label='A copies; conditional process bootstrap 95%'),Line2D([0],[0],marker='x',color='#b67b38',ls='',label='B copies; direction check'),Line2D([0],[0],marker='o',mfc='white',color='#888888',ls='',label='Identical execution layout; timing variation')],loc='outside lower center',ncol=1,fontsize=8)
    for ext in ['png','pdf']:fig.savefig(out/('d3-workflow-comparison.'+ext),dpi=200)
    plt.close(fig)
    matrices=sorted({r['matrix'] for r in rows});labels=[m.split('_',1)[-1] for m in matrices];pos=np.arange(len(matrices));width=.25;fig,axes=plt.subplots(1,2,figsize=(13,4.8),layout='constrained')
    for j,v in enumerate(['L','F','J']):
        ss=[read(D/'plans'/v/m/'structure.json') for m in matrices];bottom=np.zeros(len(matrices))
        for k,color in [('G','#2c8997'),('S','#d2a047'),('T','#9870a4')]:
            values=np.array([s[k]['nnz']/max(1,sum(s[t]['nnz'] for t in ['G','S','T','Z'])) for s in ss]);axes[0].bar(pos+(j-1)*width,values,width,bottom=bottom,color=color,label=k if j==0 else None);bottom+=values
        axes[1].bar(pos+(j-1)*width,[s['k16_tiles'] for s in ss],width,label=v,color=['#527e9a','#c09242','#2a9b8f'][j])
    for ax in axes:ax.set_xticks(pos,labels,rotation=40,ha='right');ax.grid(axis='y',alpha=.2)
    axes[0].set_title('Routing; left to right L, F, J');axes[0].set_ylabel('Fraction of original stored NNZ');axes[0].legend(ncol=3);axes[1].set_title('Padded A tile counts');axes[1].set_ylabel('16 x 16 tiles');axes[1].legend()
    for ext in ['png','pdf']:fig.savefig(out/('d3-routing-tiles.'+ext),dpi=200)
    plt.close(fig)
    prep=read(D/'preparation_aarch64.json');records={r['matrix']:r for r in prep['records'] if r['matrix'] in matrices};fig,axes=plt.subplots(1,2,figsize=(13,4.7),layout='constrained')
    for j,v in enumerate(['L','F','J']):
        order_s=[sum(records[m]['L'][k] for k in ['select_seconds','subset_seconds','reorder_seconds']) if v=='L' else records[m]['global_reorder_seconds'] for m in matrices];fmt_s=[records[m]['paths'][v]['layout_seconds'] for m in matrices];axes[0].bar(pos+(j-1)*width,order_s,width,label=v,color=['#527e9a','#c09242','#2a9b8f'][j]);axes[1].bar(pos+(j-1)*width,fmt_s,width,label=v,color=['#527e9a','#c09242','#2a9b8f'][j])
    for ax in axes:ax.set_xticks(pos,labels,rotation=40,ha='right');ax.set_yscale('log');ax.set_ylabel('CPU seconds, log scale');ax.grid(axis='y',alpha=.2);ax.legend()
    axes[0].set_title('Fresh order construction (domain + sort)');axes[1].set_title('Layout construction component')
    for ext in ['png','pdf']:fig.savefig(out/('d3-cpu-components.'+ext),dpi=200)
    plt.close(fig)
    lines=['# D3 实验结果解读','','D3比较同后端下的完整L/F/J流程；固定8/4、W16、候选256/kNN16、两个必要清零和原始M完整输出。L/F/J/O统一从成窗序列移除全部零行，尾窗不足16时均走AIV。L/F严格选中相同S={0<nnz<=8}，S执行顺序均为原行号升序。','','| 综合比较 | 时间比 | 条件95%区间 | 方向为正 | 空对照保护 | B副本比 | Holm p（探索） | 值得继续机制验证 |','|---|---:|---|---:|---:|---:|---:|---|']
    for key in PRIMARY:
        c=x['aggregate'][key];ci=c['bootstrap95_conditional'];lines.append(f"| {key} | {c['geomean']:.6f} | [{ci[0]:.6f}, {ci[1]:.6f}] | {c['faster_count']}/10 | {x['aggregate_null_guard']:.6f} | {x['aggregate'][ALT[key]]['geomean']:.6f} | {c['sign_test_holm']:.6f} | {c['workflow_followup_signal']} |")
    lines+=['','比值>1表示分母更快。先取每点/进程30次同迭代配对比中位数；每rep跨24固定点几何平均，得到10个聚合重复。正式240独立进程/64800采样；分项另72进程/32400采样，不混用。','','## 回答研究问题','']
    for key,meaning in [('L/F','先在全矩阵组织结构，再固定长度分流，是否优于先长度分流再在Cube候选中重排'),('F/J','在相同全局排列下，窗口相关选行与成组相互作用，是否优于固定长度选择'),('L/J','当前联合窗口流程相对简化长度优先流程的整体表现')]:
        c=x['aggregate'][key];lines+=[f"- {meaning}：本轮{key}={c['geomean']:.6f}，综合描述性正向={c['descriptive_positive']}，达到单点保护且B副本同向的矩阵={c['positive_matrices']}；明确退化点={c['clear_regression_points']}。"]
    lines+=['','上述结论是受控完整流程的机制证据。L/F还改变候选域、列频率权重、采样局部行号和尾行成员；F/J还改变S、组成员、尾行及S次序。不能把差异归为单一特征的纯因果效应。L是简化机制基线，不能称Neutron复现。没有强稀疏库同设备对照或原创规则验证。','','## 全部逐点结果','', '| 点 | L/F | F/J | L/J | O/J | J0/J | V2-Z/J | 保护值 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['matrix']}/N{r['n']} | "+' | '.join(f"{r['contrasts'][k]['geomean']:.6f}" for k in ['L/F','F/J','L/J','O/J','J0/J','V2-Z/J'])+f" | {r['null_guard']:.6f} |")
    lines+=['','## 控制和边界','','O使用同一全局非零排列固定成窗，不选S，保留AIV尾窗；它提供共同零行策略下的参照。J0保留精确D2/J0的排列、路由及数组，同进程测量，不能拼接历史绝对时间。V2-Z只去掉V2整零K组，组内零行和末组填充行为仍可能不同，不是与L/F/J完全相同的策略。','','执行布局恒等的主比较列在analysis.json/layout_identity中，并在图中用灰色空心点标记；这些非1比值仅属计时/分配变化，不能计为算法收益。L/F尾行数量相同，具体成员及NNZ可能不同，详见结构表。','','全部8矩阵曾在本项目使用；本轮没有未见测试集，也未据结果调阈值或删点。条件区间/检验只描述本次单设备会话。CPU分项、device_prepare_us、first_us分别保存；后两项不能拼作完整应用E2E。首次校验调用顺序固定，first_us还可能受首次运行位置影响；不据此声称单方法独立启动代价或q摊销。','','## 保存和下一步','',f"独立审计通过：{audit['independent_process_ratios_checked']}配对比、{audit['independent_cost_medians_checked']}成本中位数，最大绝对误差{audit['max_abs_error']}。40清零guard及20设备小例进程/300记录通过。精确使用D2程序，没有重编译host或计算内核。",'', '原始samples/trace、环境、协议/源快照/输入manifest、全CPU新排列和格式、精确程序/对象、日志/报错/恢复脚本全部保存。D3完成后停止并关机，不自动开发新规则或启动下一阶段。']
    (D/'结果解读.md').write_text('\n'.join(lines)+'\n')
    table=['# D3逐点统计附录','','以下72个主比较组成一个Holm族；综合三比较另为Holm3族。其它控制仅描述，不宣称多重校正显著。进程是单位，300次迭代不作为300独立样本。','', '| 点/比较 | 比值 | 均值±SD | 条件95%区间 | 延迟降低% | 正进程 | 符号p | Holm p | 同布局 | 描述性正向 |','|---|---:|---|---|---:|---:|---:|---:|---|---|']
    for r in rows:
        for key in PRIMARY:
            c=r['contrasts'][key];ci=c['bootstrap95_conditional'];table.append(f"| {r['matrix']}/N{r['n']} {key} | {c['geomean']:.6f} | {c['mean']:.6f}±{c['std']:.6f} | [{ci[0]:.6f}, {ci[1]:.6f}] | {100*(1-1/c['geomean']):.3f} | {c['faster_count']}/10 | {c['sign_test_two_sided']:.6f} | {c['sign_test_holm']:.6f} | {c['identical_execution']} | {c['descriptive_positive']} |")
    table+=['','Bootstrap：NumPy default_rng(seed20261031)，在10个进程对数比上重采样20000次，均值指数后取2.5/97.5分位；单设备会话条件范围。双侧精确符号检验排除恰为1的观测，避免正态假设，但依赖进程方向近似可交换/独立；同会话时间漂移不能完全排除。描述性正向规则另需超过L/F/J三个同实现副本的最大同层保护值、>=8/10同向、B副本同向、执行布局不恒等。该规则与Holm检验分开报告，不将描述性正向等同显著性。','','效应量为时间比及100×(1−1/比值)的延迟降低%，负值为点估计退化。完整10个进程比、原始样本和所有控制见analysis.json和各run.json。所有数据保留。','','主要source SHA：', '- protocol.json '+sha(D/'protocol.json'),'- analysis.json '+sha(D/'analysis.json'),'- independent_audit.json '+sha(D/'independent_audit.json')];(D/'stats-appendix.md').write_text('\n'.join(table)+'\n')
    structure=['# D3结构与CPU准备组件','','远端新计算必须逐字节复现全局和L受限排列。L/F相同S已独立核验；尾部成员可不同。准备均为一次新计算的组件记录，顺序/缓存未做独立随机重复，不作严谨CPU优劣或完整E2E结论。','','| 矩阵 | L选择 | L子CSR | L重排 | F/J全局重排 | 五路径路由合计 | 全局复现 | L复现 |','|---|---:|---:|---:|---:|---:|---|---|']
    for m in matrices:
        r=records[m];structure.append(f"| {m} | {r['L']['select_seconds']:.6f} | {r['L']['subset_seconds']:.6f} | {r['L']['reorder_seconds']:.6f} | {r['global_reorder_seconds']:.6f} | {r['all_routes_seconds']:.6f} | {r['global_exact_saved_order']} | {r['L_exact_frozen_order']} |")
    structure+=['','| 矩阵/流程 | G行/NNZ | S行/NNZ | T行/NNZ | Z行 | 尾NNZ% | Cube组 | 16块 | 格式秒 | 导出秒 |','|---|---|---|---|---:|---:|---:|---:|---:|---:|']
    for m in matrices:
        for v in ['L','F','J','O','J0']:
            p=records[m]['paths'][v];s=p['structure'];structure.append(f"| {m}/{v} | {s['G']['rows']}/{s['G']['nnz']} | {s['S']['rows']}/{s['S']['nnz']} | {s['T']['rows']}/{s['T']['nnz']} | {s['Z']['rows']} | {100*s['tail_nnz_fraction']:.5f} | {s['groups']} | {s['k16_tiles']} | {p['layout_seconds']:.6f} | {p['export_seconds']:.6f} |")
    (D/'结构与准备成本.md').write_text('\n'.join(structure)+'\n')
    costs=['# D3独立分项诊断','','每点3进程，先取进程内中位数，再取3进程中位数，μs。事件包含主机提交间隙与插桩；主核含B收集，API/sync可含等待。G/ST按负责行验证，未负责行仍须零；全部按M清零，空范围标EMPTY。不能将独立分支sum/max解释为实际MIX重叠。','','| 点/路径 | 负责行 | 墙钟 | 输出清零事件 | packed清零事件 | 主核 | 恢复 | span | 清零API合计 | 主核提交 | sync |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        for c in r['costs']:
            if c['label'] in ['L-B','F-B','J-B']:continue
            h=c['api_median_us'];vals=[statistics.median(c['wall_process_medians_us'])]+c['event_median_us']+[h[1]+h[3],h[5],h[9]];costs.append(f"| {r['matrix']}/N{r['n']} {c['label']} | {c['valid_rows']}"+(' EMPTY' if c['empty_valid_scope'] else '')+' | '+' | '.join(f'{v:.3f}' for v in vals)+' |')
    (D/'分项诊断.md').write_text('\n'.join(costs)+'\n')
    analysis=['# D3分析问题与结论边界','',*lines[2:12],'','全部精确表见结果解读.md、stats-appendix.md和结构与准备成本.md。','','## Claim Candidates','']
    for key in PRIMARY:
        c=x['aggregate'][key];analysis += [f"- Claim：{key}的本次完整流程比较比值为{c['geomean']:.6f}。",'  - Source evidence：analysis.json、protocol.json、对应原始samples/trace及独立审计。','  - Allowed wording：限本次固定矩阵/N、共同后端和完整输出的探索性流程证据。','  - Forbidden stronger wording：单一特征纯因果、Neutron复现/竞争力、普适收益或原创性已证实。','  - Uncertainty：单会话、分配噪声、候选域/尾行耦合、缺强库和完整摊销。',f"  - Next check：若继续研究，按预定机制标准考虑后续对照；本轮workflow_followup_signal={c['workflow_followup_signal']}。",'  - Decision：keep（受限描述）。']
    (D/'analysis-report.md').write_text('\n'.join(analysis)+'\n')
    catalog=['# D3图目录','','## d3-workflow-comparison.png / .pdf','','目的：比较L/F、F/J、L/J完整调用。来源analysis.json。蓝点与区间是A副本10进程条件bootstrap95%，橙叉是B副本方向，灰空心为执行布局恒等（只能解释计时变化）。须同时检查空对照保护、Holm及退化点；区间>1不自动通过机制验收。观察改变的是是否值得继续联合规则研究，不提供新颖性结论。','','## d3-routing-tiles.png / .pdf','','目的：说明流向与填充工作随流程如何改变。来源plans各structure.json。每矩阵左中右L/F/J；左是原始存储NNZ的G/S/T比例，右是16块数量，无误差条（固定计划）。须检查L/F的同一S、尾行变化，块少不能直接当计算时间。','','## d3-cpu-components.png / .pdf','','目的：显示结构组织域改变可能带来的准备组件成本。来源preparation_aarch64.json；一次fresh复算，严格核对排列一致，无误差条，纵轴对数。左L含选择/子CSR/重排，F/J是全局重排组件；右布局组件。不能据此拼接完整预处理、上传、首次运行和复用q总时间。'];(D/'figure-catalog.md').write_text('\n'.join(catalog)+'\n');print(dict(report=True,primary={k:x['aggregate'][k]['geomean'] for k in PRIMARY}))
if __name__=='__main__':main()
