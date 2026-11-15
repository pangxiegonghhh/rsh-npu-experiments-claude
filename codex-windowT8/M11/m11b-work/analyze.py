"""Offline M11b verification and registered bridge analysis; no binary execution."""
from pathlib import Path
import csv,json,struct,hashlib,math,os
import numpy as np
from scipy import stats
WORK=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M11B_DATA_ROOT',str(WORK/'recovered-evidence')))
OUT=WORK/'analysis-output'

def table(rows,keys=None):
    keys=keys or list(rows[0])
    def fmt(x):return f'{x:.6f}' if isinstance(x,float) else str(x)
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r[k]) for k in keys)+' |' for r in rows])
def savecsv(name,rows):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def words(p):
    b=p.read_bytes();return struct.unpack('<'+'I'*(len(b)//4),b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert (ROOT/'formal.rc').read_text().strip()=='0'
    OUT.mkdir(exist_ok=True)
    cases=list(csv.DictReader((ROOT/'manifests/cases.csv').open()));assert len(cases)==84
    registry={r['case_id']:r for r in cases};data={name:{} for name in registry};original_rows=[]
    gates=json.loads((ROOT/'GATES-BEFORE-TIMING.json').read_text());assert gates['status']=='PASS'
    for name,digest in gates['binary_sha256'].items():assert sha(ROOT/'build'/name)==digest
    for label,expected in [('standard',84),('strong-address',84)]:
        assert len(gates['checks'][label])==expected
        for q in gates['checks'][label]:
            d=ROOT/('gate-'+label)/q['case_id'];assert sha(d/'output-f32.bin')==q['output_sha256'];assert (d/'output-f32.bin').read_bytes()==(d/'reference-f32.bin').read_bytes()
    regs=sorted((ROOT/'results-B2').glob('b*-accepted.json'));assert len(regs)==20
    raw_clocks=[];sentinels=[];newcols=[]
    for f in regs:
        reg=json.loads(f.read_text());assert reg['valid'];block=reg['block'];folder=ROOT/reg['path']
        rows=list(csv.DictReader((folder/'timing.csv').open()));assert len(rows)==84
        for r in rows:
            name=r['case'];assert name in registry and int(r['block'])==block
            E=int(r['cycles']);cores=int(r['blocks']);assert cores==24
            q=words(folder/name/'stats.bin');assert len(q)==cores*32
            starts=[];ends=[]
            for core in range(cores):
                x=q[core*32:(core+1)*32];a=x[0]+(x[1]<<32);z=x[2]+(x[3]<<32);assert z>a
                assert x[4]==int(r['api_calls'])==E*int(registry[name]['expected_calls_per_replay'])
                starts.append(a);ends.append(z)
                raw_clocks.append(dict(case_id=name,block=block,core=core,begin_tick=a,end_tick=z,api_calls=x[4],tiles_completed=x[5]))
            us=(max(ends)-min(starts))/50;v=us/(E*cores)
            assert math.isclose(us,float(r['us']),rel_tol=1e-10) and math.isclose(v,float(r['us_per_matrix']),rel_tol=1e-10)
            data[name][block]=v;original_rows.append(r)
        for q in csv.DictReader((folder/'sentinel-values.csv').open()):sentinels.append(dict(block=block,**q))
        newcols.append(dict(block=block,recovered_postprocess_validation=reg.get('recovered_postprocess_validation',False),groups=reg['groups']))
    assert all(set(v)==set(range(20)) for v in data.values()) and len(raw_clocks)==40320 and len(sentinels)==800
    savecsv('raw-observations.csv',original_rows);savecsv('raw-clocks.csv',raw_clocks);savecsv('sentinel-values.csv',sentinels)
    arrays={k:np.array([v[b] for b in range(20)]) for k,v in data.items()}
    rng=np.random.default_rng(20261115);ix=rng.integers(0,20,size=(10000,20))
    def ratio(a,b):
        a,b=arrays[a],arrays[b];r=float(a.mean()/b.mean());boot=a[ix].mean(axis=1)/b[ix].mean(axis=1);delta=a-b;sign=float(stats.binomtest(int((delta<0).sum()),20,.5).pvalue)
        return dict(ratio=r,ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),time_drop_pct=100*(1-r),speedup=1/r,sign_p=sign,values_per_block=(a/b).tolist())
    summary=[];contrasts=[]
    for name,a in sorted(arrays.items()):
        sd=float(a.std(ddof=1));half=float(stats.t.ppf(.975,19)*sd/np.sqrt(20));summary.append(dict(case_id=name,mean_us_per_replay=float(a.mean()),SD=sd,ci_low=float(a.mean()-half),ci_high=float(a.mean()+half),n=20,**{k:v for k,v in registry[name].items() if k!='case_id'}))
        if not name.endswith('p0'):
            base=name[:-1]+'0';contrasts.append(dict(case_id=name,baseline=base,**ratio(name,base)))
    order=sorted(range(len(contrasts)),key=lambda i:contrasts[i]['sign_p']);previous=0
    for rank,i in enumerate(order):previous=max(previous,min(1.,contrasts[i]['sign_p']*(len(order)-rank)));contrasts[i]['exploratory_holm_sign_p']=previous
    savecsv('summary.csv',summary);(OUT/'paired-contrasts.json').write_text(json.dumps(contrasts,indent=2))
    bridge=[];shift=[];old_path=WORK/'reference-analysis/M11-paired-contrasts.json';assert sha(old_path)==json.loads((WORK/'reference-analysis/provenance.json').read_text())['sha256'];old=json.loads(old_path.read_text())
    for dtype in ['FP16','FP32']:
        for n in [128,256]:
            syn=f'M11b-B2-u36-r18-cora-like-{dtype}-n{n}-hot';ctrl=f'M11b-B2-cora-B1-control-{dtype}-n{n}-hot'
            s=ratio(syn+'-p1',syn+'-p0');c=ratio(ctrl+'-p1',ctrl+'-p0');oldc=next(r['ratio_of_means'] for r in old if r['case']==f'cora-B1-{dtype}-n{n}-hot-p1')
            aa,bb,cc,dd=[arrays[x] for x in [syn+'-p1',syn+'-p0',ctrl+'-p1',ctrl+'-p0']]
            boot_s=aa[ix].mean(axis=1)/bb[ix].mean(axis=1);boot_c=cc[ix].mean(axis=1)/dd[ix].mean(axis=1);dev=np.abs(boot_s-boot_c)/boot_c
            d=abs(s['ratio']-c['ratio'])/c['ratio']
            bridge.append(dict(dtype=dtype,N=n,synth_row_over_ND=s['ratio'],synth_ci_low=s['ci_low'],synth_ci_high=s['ci_high'],same_batch_replay_row_over_ND=c['ratio'],replay_ci_low=c['ci_low'],replay_ci_high=c['ci_high'],relative_deviation=d,deviation_ci_low=float(np.quantile(dev,.025)),deviation_ci_high=float(np.quantile(dev,.975)),within_15pct=d<=.15,over_30pct=d>.30,old_M11_replay_ratio=oldc,deviation_to_old=abs(s['ratio']-oldc)/oldc,control_change_from_old=c['ratio']/oldc-1))
            for layout in ['random-gap','cora-like']:
                high=f'M11b-B2-u56-r50-{layout}-{dtype}-n{n}-hot';low=f'M11b-B2-u36-r18-{layout}-{dtype}-n{n}-hot'
                r0=ratio(high+'-p1',high+'-p0');r1=ratio(low+'-p1',low+'-p0')
                x0,y0,x1,y1=[arrays[x] for x in [high+'-p1',high+'-p0',low+'-p1',low+'-p0']]
                delta=x0[ix].mean(axis=1)/y0[ix].mean(axis=1)-x1[ix].mean(axis=1)/y1[ix].mean(axis=1)
                shift.append(dict(dtype=dtype,N=n,layout=layout,u56r50_ratio=r0['ratio'],u36r18_ratio=r1['ratio'],ratio_difference=r0['ratio']-r1['ratio'],ci_low=float(np.quantile(delta,.025)),ci_high=float(np.quantile(delta,.975))))
    good=sum(r['within_15pct'] for r in bridge);bad=sum(r['over_30pct'] for r in bridge)
    decision='可互推（本组均值点与同批回放范围内）' if good>=3 else '不可互推；合成网格仅作机制探查，不可用于预测真实回放选路' if bad>=2 else '说不清，两者并列'
    savecsv('B2-bridge.csv',bridge);savecsv('B2-structure-ratio-shift.csv',shift)
    # Post hoc state-variation audit: retain every control observation, no split used for decisions.
    audit_name='M11b-B2-cora-B1-control-FP16-n128-hot-p1'
    control_audit=[dict(block=b,case_id=audit_name,us_per_replay=float(arrays[audit_name][b])) for b in range(20)]
    savecsv('R2b-FP16-N128-new-control-posthoc.csv',control_audit)
    ca=arrays[audit_name]
    control_note=(f'【事后补充】同批FP16/N128按行Cora控制均值{ca.mean():.6f} μs/回放、SD={ca.std(ddof=1):.6f}，'
                  f'逐轮范围{ca.min():.6f}–{ca.max():.6f}，呈约9.72与12.83两档；'
                  'ND控制仍约9.621。该格比原M11的均值配对比变化约−8.39%，其他三个控制比值变化均小于0.3%。'
                  '所有轮保留；不按双峰划组重算主门，不把哨兵通过当作所有配置稳定的证明。'
                  '该现象进一步阻止将异常简单归因为固定blockCount=8惩罚；测量故障/运行状态/流水几何交互仍分不开。'
                  '以同批与原M11两套参考计算B2，4格偏差都仍超过30%。')
    (OUT/'R2b-control-variation-posthoc.md').write_text('# 新增控制波动复核\n\n'+control_note+'\n\n'+table(control_audit)+'\n')

    b3=json.loads((ROOT/'B3-GATE-RESULTS.json').read_text());assert len(b3['records'])==100
    for q in b3['records']:
        folder=ROOT/('gate-B3-'+q['variant'])/q['case_id'];assert q['output_saved'];assert sha(folder/'output-f32.bin')==q['output_sha256']
        same=(folder/'output-f32.bin').read_bytes()==(folder/'reference-f32.bin').read_bytes();assert same==(q['status']=='PASS')
    counts={}
    for q in b3['records']:k=q['variant']+'/'+q['status'];counts[k]=counts.get(k,0)+1
    savecsv('B3-correctness.csv',b3['records']);assert counts=={'transpose/PASS':50,'plain-only/FAIL':50}
    planned=[]
    for dtype in ['FP16','FP32']:
        for n in [16,32,64,128,256]:
            for h in [1,2,4,8,16]:
                for variant in ['plain-only','transpose','plain-explicit']:
                    gate_status={'plain-only':'FAIL_NON_EQUIVALENT','transpose':'PASS_BUT_NO_VALID_BASELINE','plain-explicit':'UNSUPPORTED_DIRECT_L0B_API'}[variant]
                    for batch in [64,256,1024,4096]:
                        planned.append(dict(case_id=f'M11b-B3-{variant}-{dtype}-n{n}-h{h}-b{batch}',dtype=dtype,N=n,h=h,variant=variant,batch=batch,planned_blocks=20,observed_formal_blocks=0,status=gate_status,time_us='NOT_MEASURED',reason='no equivalent plain baseline; no forced invalid performance samples'))
    assert len(planned)==600
    savecsv('B3-planned-grid-status.csv',planned)

    verification=dict(status='PASS',observations=1680,core_clock_rows=40320,sentinel_rows=800,standard_gates=84,strong_address_gates=84,B3_gates=counts,binary_executed_locally=False)
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2));(OUT/'decision.json').write_text(json.dumps(dict(B1_device='CANCELLED_EXISTING_RANDOM',B2_decision=decision,within_15pct_cells=good,over_30pct_cells=bad,B3_delta='NOT_ESTIMABLE',B3_reason='plain-only not equivalent; no supported direct L0B explicit vector transpose'),indent=2))
    os.environ.setdefault('MPLCONFIGDIR','/private/tmp/m11b-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figs=OUT/'figures';figs.mkdir(exist_ok=True)
    labels=[r['dtype']+' N'+str(r['N']) for r in bridge];x=np.arange(4)
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    for prefix,offset,label in [('synth',-.1,'U36/R18 cora-like'),('replay',.1,'Cora B1 same batch')]:
        y=np.array([r['synth_row_over_ND'] if prefix=='synth' else r['same_batch_replay_row_over_ND'] for r in bridge]);lo=np.array([r[prefix+'_ci_low'] for r in bridge]);hi=np.array([r[prefix+'_ci_high'] for r in bridge]);ax.errorbar(x+offset,y,yerr=[y-lo,hi-y],fmt='o',capsize=3,label=label)
    ax.axhline(1,color='gray',ls='--');ax.set_xticks(x,labels);ax.set_ylabel('Ordinary row / ND2NZ mean time');ax.set_title('M11b B2: synthetic mean point versus real replay\n20 shared blocks; paired bootstrap pointwise 95% CI');ax.legend()
    for ext in ['png','pdf']:fig.savefig(figs/f'B2-bridge.{ext}',dpi=180)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    for layout,offset in [('random-gap',-.1),('cora-like',.1)]:
        rows=[r for r in shift if r['layout']==layout];y=np.array([r['ratio_difference'] for r in rows]);lo=np.array([r['ci_low'] for r in rows]);hi=np.array([r['ci_high'] for r in rows]);ax.errorbar(x+offset,y,yerr=[y-lo,hi-y],fmt='o',capsize=3,label=layout)
    ax.axhline(0,color='gray',ls='--');ax.set_xticks(x,labels);ax.set_ylabel('Row/ND at U56,R50 minus U36,R18');ax.set_title('M11b B2: structural shift in relative path preference\nPositive means row is relatively less favorable at U56,R50');ax.legend()
    for ext in ['png','pdf']:fig.savefig(figs/f'B2-structure-shift.{ext}',dpi=180)
    plt.close(fig)
    (OUT/'stats-appendix.md').write_text('''# M11b统计附录

84配置（72主点+12同批Cora B1控制）×20共享随机时间区组=1680条。核/窗口不是独立样本。84配置均值、SD、t(19)点95%CI见summary.csv。56个普通/ND配对对比以ratio of means为效果，10000次共享区组bootstrap、seed20261115，保留20比值；符号检验与Holm只作探索比较。B2主判据是4格相对偏差的预登记点估计门，不等于显著性检验；偏差点CI另存，无同时区间保证。

主比较采用同批Cora参考，原M11参考为另列敏感性。FP16/N128按行控制存在约9.72/12.83两档，原值全部保留，见R2b-control-variation-posthoc.md；不按双峰删除或重分组。额外12控制点在计时前登记。未做逐路径g调优、未补cold、没有跨矩阵泛化。cora-like只采边缘gap，不保留联合结构；36/18是均值近似，不能代表真实170窗口分布。

B3无有效plain基线，Δ/Δ'/s/fold为NOT_ESTIMABLE，未进行无效性能回归。h<16实际加载仍补齐16行，逻辑h*N*es不等于物理字节。常数差价不能证明纯发射开销；CI含0也不能证明常数。源/门/环境/全部原时钟在归档。

首区组登记脚本因6位摘要与12位原值的容差错误中断，数据本身完整；按原5%门用保存的五条原值复核并登记。保留失败代码/日志，没有改binary或重新挑点。恢复区组elapsed_s仅含登记复核耗时，不代表其测量墙钟时长。
''')
    (OUT/'figure-catalog.md').write_text('''# 图目录

## B2-bridge
目的：检验均值合成点能否预测真实B1回放的相对选路。源B2-bridge.csv；横轴4精度/N，纵轴固定按行/ND耗时比；20共享区组bootstrap点95%CI。观察两组点之间的偏离，相对偏差用数表15%/30%阈值判，不能凭视觉等时推断泛化。该图决定合成网格是否可进入选路论证，限定均值点和gap边缘。

## B2-structure-shift
目的：固定报告从(56,50)到(36,18)结构变化对普通/ND相对比值的影响。源B2-structure-ratio-shift.csv；误差条同上。正值表示前者按行相对更不利。两布局分别看；不是B0/B1绝对重排加速比，也不是纯R因果效应，不能与1.48倍混用。
''')
    analysis=f'''# M11b 分析

B1原随机间距已核，取消设备部分。B2正式1680条/20区组完整；判读：**{decision}**。4格中{good}格d≤15%，{bad}格d>30%。B3转置50/50通过、plain-only50/50不等价，差价不可估。

{table(bridge)}

{control_note}

这四格的按行相对ND优劣方向仍一致；不可互推指预登记的定量相对偏差门失败，不是四格方向都翻转。

## Claim Candidates

- Claim: 本B2均值点对同批Cora B1的相对选路检验结果为“{decision}”。
  - Source evidence: B2-bridge.csv、1680条原值、40320核时钟、预登记thresholds.csv。
  - Allowed wording: 限定本三组均值结构、两gap布局、两精度/N和共同gmax。
  - Forbidden stronger wording: 任何矩阵的通用选择器，或证明纯段数性能机制。
  - Uncertainty: 单Cora、单芯片启动、边缘gap采样、不含真实稀疏A完整消费。
  - Next check: 下游依据本判读限定合成选路表达，不自动扩大矩阵/g调优范围。
  - Decision: keep

- Claim: 本B3普通不转置候选无法作为等价加载参照。
  - Source evidence: B3-correctness.csv、100项实际输出/参考；独立直接MMAD消费。
  - Allowed wording: 本50形状plain-only不通过，转置成本差价不可由该参照估计。
  - Forbidden stronger wording: 所有显式转置硬件路径都不可能；常数等于纯发射成本。
  - Uncertainty: 未扩成UB/AIV往返的另一完整算法。
  - Next check: 如需替代方案，另定义完整等价链及包含的搬运/同步。
  - Decision: keep
'''
    (OUT/'analysis-report.md').write_text(analysis)
    receipt=json.loads((WORK/'archive-receipt.json').read_text()) if (WORK/'archive-receipt.json').exists() else {}
    report=f'''---
type: results-report
date: 2026-11-16
experiment_line: t8
round: 11b
purpose: recompute-and-bridge
status: complete
source_artifacts:
  - analysis-output/analysis-report.md
  - analysis-output/stats-appendix.md
  - analysis-output/figure-catalog.md
linked_experiments:
  - PROTOCOL.md
linked_results: []
---

# T8 / Round 11b / Recompute and bridge / 2026-11-16

## 结果与决定

离线R1–R12已交回，原M11 tar、原analysis-output和原报告均保持只读；重算基准21文件及全部204,631个原始文件哈希均不变。M11b-B1确认原生成器实际随机1/2行间距，按计划取消上卡部分。**B2结论：{decision}**（4格中{good}格d≤15%，{bad}格d>30%）。**B3转置50/50正确、plain-only50/50不等价，无法估算同输出转置差价，未凑12000条无效计时。**

## 重算的重要更正

原归一化计算数值没有算错，问题是字段语义与单位标签：原μs/矩阵应为μs/完整回放：T=(max end−min begin)/50/(E×24)，E是回放重复次数而非时钟周期。Cora每回放170窗口，20轮示例均值12.594219828→12.5942；单窗为该数/170。原6/8比例判读不变。R2异常格判(c)现有证据分不开，不剔除；审核4.42等预测是h16除16的摊销，不是真h1斜率。cold按行按已审计地址重建确实覆盖≥4×L2唯一数据，但无PMU；冷档更大的相对降幅来自ND变慢。hot-only【事后】3/4不替换原8格判据。

R5/R6/R7补齐ND/按行/按条B0/B1、绝对值、固定路径及选优差；R8补全cold/实际gap与API合并率；R9无PMU不能归因；R10指出旧门重做LoadB覆盖计时L0，不能验证primitive等价；R11标签无对调但时差机制不能单凭几何断言；R12的54/54格均有已保存输出覆盖。逐项MD/CSV见../m11-work/analysis-recompute-20261115。

## B2 设置与统计

三组(U,R)×random-gap/cora-like×N128/256×两精度×三路径=72点；另计时前增加12个同批Cora B1控制，减少跨启动参考混淆。84×20=1680条，40320条每核时钟独立复算PASS。普通84项和逐tile强地址84项均在任何正式计时之前完成；kernel.cpp SHA与原M11逐字节相同：63194374d72de61c0bded87ef407d252bb3c3e3519f1d21cd8e242b3242f34b0。host仅加五条哨兵原值落盘，20区组共800条哨兵原值。

同一24 AIC/共同gmax与原M4消费，hot工作集、实际分配/跨度均记录；合成每份一个窗口，Cora每份170窗口，跨几何只比普通/ND之比。效果采用ratio of means、10000成对区组bootstrap seed20261115，点95%CI。原0.15/0.30阈值保持，0.30仍为原稿【推】阈值。完整均值/SD/CI、两普通路径、全部时钟与哨兵见analysis-output。

{table(bridge,['dtype','N','synth_row_over_ND','same_batch_replay_row_over_ND','relative_deviation','within_15pct','over_30pct','deviation_to_old'])}

这四格的按行/ND优劣方向与同批真实回放仍一致；“不可互推”是原稿的**定量比值误差**门失败，并非观察到四格选路方向相反。合成三格仅约1%–2%按行优势，真实回放约25%–26%，幅度不可直接外推。

{control_note}

另固定报告结构比值之差（(56,50)的按行/ND减(36,18)）：

{table(shift)}

图B2-bridge展示均值合成点与真实回放的相对路径比，不可混为绝对时间。图B2-structure-shift分两gap排法展示结构改变，不能把该差值当作真实B0/B1的1.48倍加速或纯R因果效应。两图均经数据表核对并目视检查，点CI非同时覆盖。

## B3 正确性与无法估计的原因

新独立kernel-b3直接将被测L0B送入MMAD，与强地址标记CPU参考比较，没有后续LoadB覆盖。h=1/2/4/8/16、五种N、两精度：transpose50/50 PASS；plain-only50/50 FAIL，全部实际输出/参考/失败原因保留。原稿要求无效plain不得强行计时，故Δ、Δ'、对字节斜率s、fold均NOT_ESTIMABLE。B3-planned-grid-status.csv逐项列出完整600个计划配置、每项20轮计划数与实际正式0轮及原因；未虚构缺失值。

此外，原稿plain+explicit所指的一条Transpose/TransDataTo5HD是向量UB接口，官方CANN9支持TPosition为VECIN/VECCALC/VECOUT，未提供直接L0B→L0B的同等调用。实际SDK转置头文件已归档，不执行非法位置调用，不把转置挪到计时外。要经UB/GM/AIV实现另一条完整链会引入搬运和同步，超出本“普通L0加载后多一条转置”的对照，未自动扩范围。

官方依据：[Transpose](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0199.html)、[TransDataTo5HD](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0200.html)。这限定当前可用候选，并非对所有硬件方案不可能的证明。h<16在Cube加载仍补齐16行，实际字节16*N*es，不应拿h*N*es假定字节变化；近似常数与CI含0均不能推出纯发射开销。

## 偏离、错误与限制

- B3原稿600点×20应为12000而非1200；无合法参照时不进入此正式网格。B1取消是计划内分岔；B2增加12同批控制在计时前登记，原72点不变。
- B3使用独立target直接消费L0结果，未覆盖原M11 binary；B2 kernel逐字节不变。B3与原binary的差异明确属于验证实现修复，未据此声称完成等价性能对照。
- 当前包/本工作区缺少引用的交回模板，使用现有M11表并补齐item/case_id/kernel_variant/layout与thresholds字段，未冒称读过缺失模板。
- 首区组登记因摘要默认6位有效数字、哨兵原值12位导致过严一致性断言；保留失败源码/日志，仅改登记容差和从原5条重建漂移，原binary、5%阈值、全部计时不变。保存已完整首区组并重核，不按结果重挑点。恢复首区组elapsed_s仅登记复核耗时，非测量墙钟时长。
- 原1MB包上传413，改73712B源码+本机重建输入，全部1340二进制输入SHA与本地一致。启动浏览器连接短暂失败后恢复，未新租卡。
- 只有Cora与三个均值点；cora-like复制gap边缘而非联合分布。没有PMU、未逐路径g调优、未补cold，不是完整稀疏SpMM，结论不能外推到任意矩阵。没有修改论文、原M11归档或推送Git。当前仓库未绑定Obsidian，本报告只作本地交付，未写回知识库。

## 复核与产物

设备新目录/data/t8-m11b-20261115，复用OP08JZ85MYKCJKH3；本次容器7e4ad1fd20aa、物理NPU5、PCI0000:41:00.0，开工核验空闲。启动前累计8h57m，关机后9h27m；平台已在2026-11-16凌晨核对“已关机”，新增约30分钟。按此前4元/小时估算约2元（开机弹窗0.00显示未用作账单，实际以平台账单为准）。完整72,655,915字节归档与10,090文件SHA均在本地通过核验；无远端独有的必要证据，临时认证header已删除。详见shutdown-verification.json，不依赖远端约36小时保留。

- analysis-output/analysis-report.md、stats-appendix.md、figure-catalog.md、figures/：严格分析包。
- ../m11-work/analysis-recompute-20261115/：R1–R12完整离线重算、cases适配表、SHA256SUMS。
- m11b-evidence-complete.tar.gz及archive-receipt.json：全部新增设备原值、输入、源码、二进制、环境、编译及失败记录；SHA256={receipt.get('sha256','见receipt')}。
- analysis-output/verification.json：1680条与40320核原时钟/计数/归一化及168项前置正确性核验。
- recovered-evidence/GATES-BEFORE-TIMING.json、B3-GATE-RESULTS.json、manifests/thresholds.csv、prep/structures.json：事前门、候选失败、阈值、完整几何。
- analyze.py、prepare.py、run_experiment.py：派生计算及设备规程源码；离线不运行回传binary。

离线复算：在本m11b-work执行`M11B_DATA_ROOT="$PWD/recovered-evidence" python3 analyze.py`。原M11重算在独立analysis-recompute目录执行recompute.py。

## 下一步决定

保持实例关闭。B2下游选路表达按本次阈值判读加限定；B3转置成本标为不可估，不把旧0.00055μs当物理转置系数。若继续研究完整UB/AIV替代链或PMU机制，应另定等价路径与完整计时边界；本次不自动增加设备工作。
'''
    (WORK/'2026-11-16--t8--r11b--recompute-and-bridge.md').write_text(report)
    print(json.dumps(dict(verification=verification,B2_decision=decision,within_15pct=good,over_30pct=bad),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
