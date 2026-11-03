"""Saved D2 data only: analysis bundle, plots, experiment interpretation."""
from pathlib import Path
import json,math,statistics,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d2 import read,save,sha
D=ROOT/'results/d2'
def main():
    choice=read(D/'threshold_selection.json');scopes=['dev']+(['eval'] if choice['eval_allowed'] else []);out=D/'figures';out.mkdir(exist_ok=True);datasets={s:read(D/(s+'_analysis.json')) for s in scopes};summary=[]
    identities=[]
    for p in sorted((D/'plans/t4').iterdir()):
        if p.name.startswith('smoke_'):continue
        other=D/'plans/t8'/p.name
        hashes={tag:{q:sha(D/'plans'/tag/p.name/'full'/(q+'.bin')) for q in ['cube_ptr','colref','tiles','rowmap','srows']} for tag in ['t4','t8']}
        identities.append(dict(matrix=p.name,identical_execution_layout=hashes['t4']==hashes['t8'],sha256=hashes))
    save(D/'layout_identity.json',dict(records=identities,interpretation='Shared CSR/B/golden/valid and native backend are the same; identical five execution layout arrays implies no routing/layout algorithm difference. Observed non-one ratios there are runtime/allocation noise, not threshold gains.'))
    for scope,data in datasets.items():
        rows=data['rows'];names=[r['matrix'].split('_',1)[-1]+f" / {r['n']}"+('*' if any(t['matrix']==r['matrix'] and t['identical_execution_layout'] for t in identities) else '') for r in rows];height=max(3.8,len(rows)*.35+1.4);fig,ax=plt.subplots(figsize=(8,height),layout='constrained');y=np.arange(len(rows));means=np.array([r['contrasts']['T4-A/T8-A']['geomean'] for r in rows]);ci=np.array([r['contrasts']['T4-A/T8-A']['bootstrap95_conditional'] for r in rows])
        ax.errorbar(means,y,xerr=[means-ci[:,0],ci[:,1]-means],fmt='o',capsize=3,color='#267f9b',label='A copies, conditional process bootstrap 95%')
        ax.scatter([r['contrasts']['T4-B/T8-B']['geomean'] for r in rows],y+.12,marker='x',color='#bb7838',label='B copies, direction check');ax.axvline(1,color='gray',ls='--',lw=1);ax.set_yticks(y,names);ax.invert_yaxis();ax.set_xlabel('Full resident call time: 4/2 divided by 8/4'+('\n* Identical execution layout; differences are timing/allocation variation' if any(r['matrix']=='FEMLAB_ns3Da' for r in rows) else ''));ax.set_title('D2 development comparison' if scope=='dev' else 'D2 frozen-config evaluation (previously seen matrices)');ax.grid(axis='x',alpha=.2);ax.legend(fontsize=8)
        for ext in ['png','pdf']:fig.savefig(out/(scope+'-threshold-ratio.'+ext),dpi=200)
        plt.close(fig)
        for r in rows:
            c=r['contrasts']['T4-A/T8-A'];v=c['process_ratios'];summary.append(dict(scope=scope,matrix=r['matrix'],n=r['n'],mean_ratio=statistics.mean(v),std_ratio=statistics.stdev(v),geomean_ratio=c['geomean'],percent_latency_reduction=100*(1-1/c['geomean']),ci=c['bootstrap95_conditional'],faster=c['faster_count'],p_sign=c['sign_test_two_sided'],p_holm=c['sign_test_holm_secondary_family']))
    dev=datasets['dev'];fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained');names=[r['matrix'].split('_',1)[-1] for r in dev['rows']];x=np.arange(len(names));width=.34
    for j,tag in enumerate(['t4','t8']):
        structures=[read(D/'plans'/tag/r['matrix']/'structure.json') for r in dev['rows']];bottom=np.zeros(len(x))
        for label,color in [('G','#2b8d9a'),('S','#d9a44a'),('T','#a16b9c'),('Z','#aaaaaa')]:
            vals=np.array([s[label]['nnz']/sum(s[k]['nnz'] for k in ['G','S','T','Z']) for s in structures]);axes[0].bar(x+(j-.5)*width,vals,width,bottom=bottom,color=color,label=label if j==0 else None);bottom+=vals
        axes[1].bar(x+(j-.5)*width,[s['k16_tiles'] for s in structures],width,label=['4/2','8/4'][j],color=['#267f9b','#bb7838'][j])
    for ax in axes:ax.set_xticks(x,names);ax.tick_params(axis='x',labelrotation=15);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Fraction of original nnz');axes[0].set_ylim(0,1);axes[0].set_title('Routing, left 4/2 and right 8/4');axes[0].legend(ncol=4,fontsize=8);axes[1].set_ylabel('Padded 16 x 16 A tiles');axes[1].set_title('Cube work proxy, not actual time');axes[1].legend()
    for ext in ['png','pdf']:fig.savefig(out/('dev-routing-tiles.'+ext),dpi=200)
    plt.close(fig)
    save(D/'descriptive_stats.json',dict(unit='10 independent process paired-ratio medians per point',records=summary))
    c=dev['aggregate']['T4-A/T8-A'];selected='/'.join(map(str,choice['selected_thresholds']));lines=['# D2 实验结果解读','',f"本轮按事前规则保留阈值 **{selected}**。开发集综合4/2÷8/4={c['geomean']:.6f}，条件95%区间[{c['bootstrap95_conditional'][0]:.6f}, {c['bootstrap95_conditional'][1]:.6f}]，{c['faster_count']}/10进程组方向为正，空对照保护值{dev['aggregate_null_guard']:.6f}。",'',f"验收条件逐项：{choice['conditions']}。",'']
    lines+=['开发集主估计仅略超过空对照保护值，应视为通过本轮配置规则的边界信号；不能据此宣称普适最优或每点均改善。','']
    if not choice['eval_allowed']:lines+=['8/4未通过冻结规则，因此未运行其余五个矩阵的扩展评估。这个结果只否定本轮将默认阈值从4/2替换为8/4的依据；不能据此否定整体分组分流框架。','']
    else:lines+=['8/4通过规则后才运行其余五个矩阵×三个N；该组矩阵此前已在项目中使用，称冻结配置评估，不称未见测试集。','']
    lines+=['## 完整数值','', '| 集合/矩阵/N | 比值 | 条件95%区间 | 8/4延迟降低% | 快进程 | 均值±SD | Holm p（探索） |','|---|---:|---|---:|---:|---|---:|']
    for r in summary:lines.append(f"| {r['scope']}/{r['matrix']}/N{r['n']} | {r['geomean_ratio']:.6f} | [{r['ci'][0]:.6f}, {r['ci'][1]:.6f}] | {r['percent_latency_reduction']:.3f} | {r['faster']}/10 | {r['mean_ratio']:.6f}±{r['std_ratio']:.6f} | {r['p_holm']:.6f} |")
    lines+=['', '布局恒等检查：'+', '.join(r['matrix'] for r in identities if r['identical_execution_layout'])+' 的两阈值五个执行布局数组逐字节相同；共同CSR/B/golden/valid亦共享。该矩阵任何非1时间比均不可归因为阈值算法收益。完整SHA见layout_identity.json。bcsstk38的8/4 Cube负责nnz略增，bcsstk17填充块由4220变4221；阈值会改变后续窗口成员，不能假设更高阈值必然逐矩阵减少Cube工作。']
    lines+=['','## 公共后端下与V0/V2比较','', '| 集合/矩阵/N | V0÷4/2 | V0÷8/4 | V2÷4/2 | V2÷8/4 |','|---|---:|---:|---:|---:|']
    for scope,data in datasets.items():
        for r in data['rows']:lines.append(f"| {scope}/{r['matrix']}/N{r['n']} | "+' | '.join(f"{r['contrasts'][k]['geomean']:.6f}" for k in ['V0/T4-A','V0/T8-A','V2/T4-A','V2/T8-A'])+' |')
    lines+=['','V0为本项目朴素CSR路径，V2为固定重排后的Cube路径，均使用相同native clear；未与强优化库或Neutron做同口径比较。以上为描述性比值，不能据此宣称成熟基线竞争力。','', '## 路由及准备成本','', '| 矩阵 | 阈值 | G行/nnz | S行/nnz | T行/nnz | Z行 | 组 | 16块 | 格式字节 | 分流CPU秒 | 格式CPU秒 |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    prep=[]
    for scope in scopes:
        timing=read(D/(scope+'_preparation_aarch64.json'))
        for rec in timing['records']:
            if rec['matrix'].startswith('smoke_'):continue
            for tag,t in rec['thresholds'].items():
                st=t['structure'];route=statistics.median(t['partition_seconds']);layout=statistics.median(t['layout_seconds']);prep.append(dict(matrix=rec['matrix'],tag=tag,partition_seconds=route,layout_seconds=layout,export_seconds=t['export_seconds'],machine=rec['machine'],input_load_seconds=rec.get('input_load_seconds'),order_load_seconds=rec.get('order_load_seconds'),historical_reorder_seconds=rec.get('historical_common_reorder_seconds')))
                lines.append(f"| {rec['matrix']} | {tag} | {st['G']['rows']}/{st['G']['nnz']} | {st['S']['rows']}/{st['S']['nnz']} | {st['T']['rows']}/{st['T']['nnz']} | {st['Z']['rows']} | {st['groups']} | {st['k16_tiles']} | {st['plan_bytes']} | {route:.6f} | {layout:.6f} |")
    save(D/'preparation_summary.json',dict(records=prep,limits='Three deterministic fixed-order route/layout repetitions per threshold, CPU aarch64. Export includes filesystem/hash work and is not format time alone; historical reorder not remeasured. No complete application E2E.'))
    lines+=['','## 如何解释','', '第一张图比较完整常驻调用，两次必要清零、主核、恢复和同步均包含；正式计时没有设备事件。A、B副本用于检查分配位置敏感性，不能择优报告副本。第二张图展示路由和填充块变化：更少Cube块不等于更快，因为转入AIV的非零、组组合和调度成本也同时改变。','', 'CPU准备单独记录输入读取、固定order读取、分流、格式转换和导出。原排序耗时仅引用历史元数据，未重新计量；准备成本按4/2后8/4固定顺序测三次，仅作粗略成本记录，不能据此作严谨的预处理优劣推断；没有应用端到端或预处理摊销结论。分项文件中的G/ST只验证负责行，空负责域有标记；两路独立运行无法推导MIX真实重叠时间。','', '所有原始数据、程序、对象库、格式数组、候选决策、日志及哈希均保留。下一阶段需用户另行启动D3。']
    costlines=['# D2 独立分项与分支诊断','','与正式计时分开运行：每点3进程，各10预热/30次采样。表中先取进程内中位数，再取3进程中位数，单位μs。各列中位数不要求相加等于墙钟中位数。事件区间包含主机提交间隙和插桩，API/sync可能含等待。','','G-only/ST-only仅校验负责行，其余行必须清零；空负责域标EMPTY。仍按原M分配并清零完整输出，G仍保留packed清零。不能将两分支相加/max推导MIX重叠。','','| 点/路径 | 负责行 | profile墙钟 | 输出清零事件 | packed清零事件 | 主核事件 | 恢复事件 | span | 清零API合计 | 主核提交API | sync API |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scope,data in datasets.items():
        for r in data['rows']:
            for cst in r['costs']:
                if cst['label'] not in ['T4-A','T8-A','T4-G','T4-ST','T8-G','T8-ST']:continue
                ev=cst['event_median_us'];h=cst['api_median_us'];values=[statistics.median(cst['wall_process_medians_us'])]+ev+[h[1]+h[3],h[5],h[9]]
                costlines.append(f"| {r['matrix']}/N{r['n']} {cst['label']} | {cst['valid_rows']}"+(' EMPTY' if cst['empty_valid_scope'] else '')+' | '+' | '.join(f'{v:.3f}' for v in values)+' |')
    (D/'分项诊断.md').write_text('\n'.join(costlines)+'\n')
    (D/'结果解读.md').write_text('\n'.join(lines)+'\n')
    (D/'analysis-report.md').write_text('\n'.join(lines[:7])+ '\n\n详表见结果解读.md与dev_分析.md。\n\n## Claim Candidates\n\n- Claim：本轮阈值选择为'+selected+'。\n  - Source evidence：threshold_selection.json、dev_analysis.json、protocol.json及原始measurements。\n  - Allowed wording：固定三个开发矩阵/N64、单设备会话下按预先规则作出配置选择。\n  - Forbidden stronger wording：普适最优阈值、Neutron竞争力、完整框架无效或论文创新已验证。\n  - Uncertainty：运行时/分配噪声、设备会话只有一次、矩阵固定。\n  - Next check：D3需另行启动；先保留本轮选择和完整负结果。\n  - Decision：keep（限配置选择）。\n')
    appendix=['# D2 统计附录','','主要比较：三个开发点的4/2与8/4完整常驻调用。对每个点/进程，取30次同迭代配对比中位数；同rep跨三个点几何平均，形成10个聚合观测。10次warmup排除。主要估计为10个聚合观测的几何平均，20000次对数进程bootstrap，固定seed20261029，2.5/97.5分位条件区间。','','不把300次迭代作为300个独立重复，不把固定矩阵当随机总体。不同进程按打乱作业顺序执行，仍可能共享会话漂移；bootstrap区间只描述该假设下的不确定性。','','精确双侧符号检验使用10个进程配对比的方向，等于1的观测排除；无正态假设，要求进程方向可交换/独立，其假设在单会话下只能近似。开发3点为一个Holm族；若有扩展评估，其15点另成一族。综合主比较单列；其它baseline和交叉副本比仅描述，不宣称多重校正显著。p值不参与配置选择。','','效应量以时间比与100×(1−1/比值)延迟降低比例报告，负值代表退化。逐点算术均值±样本SD、条件区间和全部进程数见结果解读.md与descriptive_stats.json。','','空对照保护值取两阈值同实现副本比的绝对对数95分位指数的最大值；综合先跨矩阵聚合再取分位。事前规则条件逐项保存；原历史runtime-clear数据未参与选择。','','## 原始来源哈希','']
    for scope in scopes:appendix.append(f"- {scope}_analysis.json SHA256 {sha(D/(scope+'_analysis.json'))}")
    appendix+=['','中途在扩展正式测量期间做过CPU快照读取/压缩以防中断。全部进程保留，没有据此删除或重跑慢点；无并行NPU实验。副本保护不能消除所有主机/运行时干扰，详见notes.md。','', '- protocol.json SHA256 '+sha(D/'protocol.json'),'- threshold_selection.json SHA256 '+sha(D/'threshold_selection.json')];(D/'stats-appendix.md').write_text('\n'.join(appendix)+'\n')
    catalog=['# D2 图目录','','## dev-threshold-ratio.png / .pdf','','目的：判断新后端下8/4是否优于4/2。来源dev_analysis.json；蓝点为A副本几何平均，误差线为10进程条件bootstrap95%区间，叉为B副本方向核查。标题须注明3个固定开发矩阵、N64、常驻完整调用。解读时同时核查空对照保护值和事前选择条件，不能仅看区间越过1。','','## dev-routing-tiles.png / .pdf','','目的：解释阈值改变了哪些工作。来源plans/t4、t8的structure.json。左为原始nnz的G/S/T/Z归属，右为填充16×16块数；每矩阵左柱4/2右柱8/4，无误差条（固定计划）。须注明块数仅是工作代理，不能将减少块数直接当加速。','','若存在eval-threshold-ratio，含义与第一张相同，15点为此前见过矩阵的冻结配置评估；不能称独立未见泛化。'];(D/'figure-catalog.md').write_text('\n'.join(catalog)+'\n');print(dict(report=True,scopes=scopes,selected=selected))
if __name__=='__main__':main()
