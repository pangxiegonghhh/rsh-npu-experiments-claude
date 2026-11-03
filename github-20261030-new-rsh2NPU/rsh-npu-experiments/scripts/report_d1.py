"""Interpret completed D1 and supplementary API evidence; CPU/files only."""
from pathlib import Path
import json,statistics,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import POINTS,LABELS,read,save,sha
D=ROOT/'results/d1'
def main():
    a=read(D/'local_audit.json');b=read(D/'api_analysis.json');assert read(D/'independent_audit.json')['passed'] and read(D/'api_independent_audit.json')['passed'];checks=0
    for r in a['rows']:
        m,n=r['matrix'],r['n']
        for i,l in enumerate(LABELS):
            e=next(v for v in r['events'] if v['label']==l);vals=[]
            for rep in range(3):
                raw=read(D/'profile'/m/f'N{n}'/f'run{rep}.json');v=[statistics.median(t[j] for t in raw['events'][i]) for j in range(5)];assert v==e['process_component_medians_us'][rep];vals.append(v);checks+=5
                assert statistics.median(raw['records'][i]['samples_us'])==e['profile_wall_process_medians_us'][rep]
            assert [statistics.median(v[j] for v in vals) for j in range(5)]==e['component_median_of_processes_us']
    save(D/'report_verification.json',{'passed':True,'event_component_process_medians_independently_checked':checks,'source_analysis_sha256':sha(D/'local_audit.json'),'source_api_analysis_sha256':sha(D/'api_analysis.json'),'device_executed':False})
    lines=['# D1：收益来源与当前后端的成本问题','','**D1完成。web的收益有较大一部分来自全零窗口及相关输出处理，但去掉这些窗口后H-V仍有可分辨的剩余收益；当前调用又被较昂贵的清零API路径显著影响，应先修公共后端再校准后续算法比较。** 本阶段没有执行D2/D3，也没有改变默认4/2、重排、分流或设备计算内核。','','## 测了什么','','五个事先指定的D0代表点。正式七记录为V0、V2、V2-Z、HV-A、HV-B、G-only、ST-only；每点10个独立进程，各10预热/30采样，10500正式样本。正式程序沿用原D0二进制，没有设备事件。另15个独立事件诊断进程（3150样本），以及根据异常大的清零区间触发的15个主机API分项诊断进程（3150样本）。补测目的和协议先保存再测；它不提供新的正式加速比。','','原始设备计算内核未重编译，仅诊断host新编译。16个设备小例进程/112条记录检查通过，覆盖全零、不满窗、N33、非连续原行映射和空分支。正式/两类诊断均做B与-B数值检查；最大绝对误差5.34058e-5。G/ST部分输出只检查负责行，空mask不算有效数值证据。','','## 正式完整调用结论','','| 点 | V2 / V2-Z | V2-Z / HV-A | V2 / HV-A | V0 / HV-A | 判断 |','|---|---:|---:|---:|---:|---|']
    decisions=['V2与H-V小差异未分辨','H-V收益可分辨，零窗口无法解释','H-V较V2约4%收益可分辨，但仍输V0','去零有清晰收益，H-V相对去零后仍有剩余收益','V2与H-V小差异未分辨，仍输V0']
    for r,text in zip(a['rows'],decisions):
        c=r['contrasts'];lines.append(f"| {r['matrix']}/N{r['n']} | "+' | '.join(f"{c[k]['geomean']:.4f}" for k in ['V2/V2-Z','V2-Z/HV-A','V2/HV-A','V0/HV-A'])+' | '+text+' |')
    lines += ['', '比值>1表示分母更快。每进程先取30迭代配对比中位数，再对10进程做几何平均；区间按10进程bootstrap，不能把300次迭代当300个独立实验。两份H-V相同实现/布局、不同分配，以记录索引区分。按事前描述性规则，email/ca/web的V2→H-V为清晰正向，ns/thermal未分辨。所有慢点保留。','','### web：去零解释了一部分，尚未解释全部','','V2共20359组，其中10120组为全零K窗口；V2-Z仅删除这些整组及packed/restore槽，保留全部非空组成员、顺序与K16块字节。完整M输出仍清零，所有原行都验证。其余四点没有全零V2组，V2-Z与V2布局恒等，测量差异只作为分配/计时对照。','','web的V2/V2-Z=1.364497，条件区间[1.298536,1.428215]，10/10进程同向；V2-Z/HV-A=1.146945，区间[1.071263,1.211279]，8/10同向，HV-B确认方向（1.157508）。因此不能把原V2→H-V约1.574×全部归于新结构分流，也不能说全是跳零所得。','','剩余约1.147×仍同时包含非空组成员变化、组数/packed尺寸变化、路由、主核和恢复开销，不能直接命名为“分流规则贡献”。删除零组也会改变后续组索引及静态core轮转，不是只测恢复核的纯消融。多个比值各自取中位数，不要求严格相乘。','','### email与宽N负例','','email没有全零V2窗口，H-V相对V2-Z仍约1.229×，说明其收益不能由整零窗删除解释。ca/N256虽然相对V2约1.040×，但V0/HV-A=0.717484；thermal/N64的V0/HV-A=0.770305。当前框架尚未解决这两个点相对全AIV的劣势。','','## 分项诊断揭示：清零路径必须先查清','','事件区间包含设备流上的工作和主机提交造成的流空隙，不能当作纯设备算子时间。尤其无groups时根本不执行packed清零/恢复，约0.14μs的相邻事件间隔只代表记录开销。事件插桩数据独立保存，不与正式绝对延迟直接混用。','','初次诊断的H-V两个清零事件区间之和约占总span的46%/76%/92%/57%/74%（分别ns/email/ca/web/thermal，分项中位数比只作粗略描述）。主核中含B行收集、数据布局与MMAD/AIV工作，不能叫纯计算。','','为区分主机提交和流上区间，补测在每个runtime调用边界记录主机时钟；事件查询和统计分配仍在主墙钟之外。结果如下，均为单独补测三进程的中位汇总：','','| H-V点 | 主机输出清零调用 μs | 主机packed清零调用 μs | 两次清零调用/完整墙钟 | 主机主核launch调用 μs | 最后同步调用 μs |','|---|---:|---:|---:|---:|---:|']
    for m,n in POINTS:
        r=next(r for r in b['rows'] if r['matrix']==m and r['n']==n and r['label']=='HV-A');v=r['host_median_of_processes_us'];fraction=statistics.median(r['host_clear_wall_fraction_process_medians']);lines.append(f'| {m}/N{n} | {v[1]:.2f} | {v[3]:.2f} | {fraction:.1%} | {v[5]:.2f} | {v[9]:.2f} |')
    lines+=['','这证明当前主机在清零API调用内确实花费可观时间，但不证明这些时间都是CPU算术，也不证明设备清零时长=API时长。API内部可能包含runtime工作或等待；最终sync也包含等待，不能叫纯设备耗时。没有时间线证据，不能给出“纯HBM吞吐瓶颈”或“主机与设备开销可相减分离”的结论。','','当前实现的输出/中间结果处理会显著改变不同版本的完整调用时间。较小packed布局可能同时减少API提交成本和流上处理，因此已有改善并非都来自Cube计算利用率。应把这一实现成本作为后端问题先处理。','','## 固定计划的G/ST诊断能说什么','','G-only沿用H-V的G组全部成员/块；ST-only沿用同一S/T行。每次仍清整M输出，G-only也清packed再恢复，故分支墙钟含公共输出处理，并非两路纯工作时间。按事件主核区间，H-V与G-only量级接近，ST主核明显较短；这支持下一步优先关注G路径及公共输出成本，但不能证明实际MIX达到了理想并行。','','没有将两次独立执行的墙钟相加或取max当真实混合时间；精确重叠/争用仍需设备时间线。冻结S/T很小的ns/thermal两点也不应据微小差异下路由结论。','','## 下一轮建议与停止点','','D1的预先指定单因素候选V2-Z已有同设备完整调用确认。**建议先增加一个独立D1b阶段，统一修公共清零后端，再进入D2的4/2与8/4确认。** 不将V2-Z或新清零后端追溯替换旧结果。','','D1b最小范围可从相同语义的设备原生清零实现入手，对所有对照一致使用新后端；再单独评估由完整写覆盖证明允许省去的清零。必须覆盖零K组、空行、N33、B/-B连续调用和部分输出，不能凭“上轮已有结果”省掉必要初始化。先保持组成员/路由/阈值不变，做新旧后端同设备配对，避免与流水、排序、负载调度同时更改。此处仅为建议，未实现或运行。','','后端固定后再做原定D2；D3的L/F/J仍用于直接检验“分流前组织结构”的问题。目前尚未证明其原创性或独立收益，也没有强稀疏库/Neutron同设备基线和完整预处理摊销。','','## 原始数据与恢复','','正式/事件原始：measurements/、profile/；补充主机诊断：api/。冻结协议、源快照、精确程序、编译对象、变换列表及输入哈希均已保存。正式与补充包分别封存，后者没有覆盖前者。独立核验350配对比、594数组、525事件分项进程中位数、1050主机分项进程中位数与105个清零占比。','','正式包SHA256：821f96c7ccc4575d31e96a20bd571ea5dc44736e53fe1d9a75a6e39b56f81407（13851638字节/859条目）。补充包SHA256：a8d50402ca20f480314dfb4d17c129f164184aef53b855aba6cde38c3d7aa0b8（1536474字节/92条目）。','','实验运行于新容器cf7ca219b591、物理NPU1，原实例仍为910B2/64GB；不可将D0物理NPU5会话与本轮绝对延迟直接拼接。温度/功耗只采进程端点，未连续采频率。本轮未出现设备/数值失败；工作台重启后旧终端标签失效，重绑新标签恢复，未重复设备任务。','','关机证明与最终恢复包核验另见shutdown.json和项目备份清单。D1结束后停止；下轮需用户明确启动。']
    (D/'结果解读.md').write_text('\n'.join(lines)+'\n')
    apilines=['# D1补充：主机API分项计时','','本表为补充诊断，每点三进程各10预热30采样，不替代正式加速比。单位μs，先取进程内中位数再取三进程中位数。完整原始及1050项独立复算见api/、api_analysis.json与api_independent_audit.json。','','| 点/标签 | 输出memset调用 | packed memset调用 | 主核launch调用 | 恢复launch调用 | final sync | 主墙钟 | 清零API占墙钟 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in b['rows']:
        v=r['host_median_of_processes_us'];apilines.append(f"| {r['matrix']}/N{r['n']} {r['label']} | {v[1]:.3f} | {v[3]:.3f} | {v[5]:.3f} | {v[7]:.3f} | {v[9]:.3f} | {statistics.median(r['wall_process_medians_us']):.3f} | {statistics.median(r['host_clear_wall_fraction_process_medians']):.2%} |")
    apilines+=['','API时长可含runtime阻塞/等待；final sync不是纯设备工作；事件区间可能含主机提交空隙。未计算纯HBM吞吐或CPU算术成本。原始逐次各项和小于等于对应完整调用墙钟，已验证。']
    (D/'主机API分项.md').write_text('\n'.join(apilines)+'\n');print({'passed':True,'event_component_process_medians':checks})
if __name__=='__main__':main()
