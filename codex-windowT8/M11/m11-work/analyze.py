"""Analyze M11 accepted random blocks; never use a partial dataset for final claims."""
from pathlib import Path
import csv,json,re,math,statistics,os
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/m11-matplotlib')
import numpy as np
from scipy import stats
ROOT=Path(os.environ.get('M11_DATA_ROOT',str(Path(__file__).resolve().parent)))

def read_stage(stage:str,mode:int=0)->list[dict]:
 root=ROOT/f'results-{stage}-a{mode}';rows=[]
 journals=sorted(root.glob('b*-accepted.json'));assert len(journals)==20,(stage,len(journals))
 for f in journals:
  reg=json.loads(f.read_text());assert reg['valid'];block=reg['block'];path=ROOT/reg['path']/'timing.csv'
  with path.open() as stream:
   current=list(csv.DictReader(stream))
  assert len({r['case'] for r in current})==len(current)
  for r in current:r['block']=int(r['block']);assert r['block']==block
  rows+=current
 return rows

def interval(x:list[float])->dict:
 a=np.asarray(x,dtype=float);assert len(a)==20 and np.all(np.isfinite(a));sd=float(a.std(ddof=1));half=float(stats.t.ppf(.975,19))*sd/math.sqrt(20)
 return dict(n=20,mean=float(a.mean()),sd=sd,ci95_low=float(a.mean()-half),ci95_high=float(a.mean()+half),median=float(np.median(a)),iqr=float(np.quantile(a,.75)-np.quantile(a,.25)),values=a.tolist())

def pair(x:list[float],y:list[float])->dict:
 a=np.asarray(x);b=np.asarray(y);delta=a-b;lr=np.log(a/b);info=interval((a/b).tolist());sw=stats.shapiro(lr);p_t=float(stats.ttest_1samp(lr,0).pvalue) if np.std(lr)>0 else (0. if lr[0] else 1.)
 # Sign test is assumption-light; t/Wilcoxon results are supplementary.
 nz=lr[lr!=0];sign_p=float(stats.binomtest(int((nz<0).sum()),len(nz),.5).pvalue) if len(nz) else 1.
 p_w=float(stats.wilcoxon(lr,method='auto').pvalue) if len(nz) else 1.
 rng=np.random.default_rng(20261115);ix=rng.integers(0,20,size=(10000,20));boot=a[ix].mean(axis=1)/b[ix].mean(axis=1);rom=float(a.mean()/b.mean())
 return dict(ratio=info,ratio_of_means=rom,ratio_of_means_paired_bootstrap_ci95=[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))],first_mean_us=float(a.mean()),second_mean_us=float(b.mean()),time_drop_pct=100*(1-rom),speedup_ratio_of_means=float(b.mean()/a.mean()),log_shapiro_p=float(sw.pvalue),paired_log_t_p=p_t,wilcoxon_p=p_w,sign_p=sign_p,effect_mean_delta_us=float(delta.mean()),paired_dz=float(delta.mean()/delta.std(ddof=1)) if delta.std(ddof=1)>0 else None,lag1_log_ratio=float(np.corrcoef(lr[:-1],lr[1:])[0,1]) if np.std(lr[:-1])>0 and np.std(lr[1:])>0 else None)

def holm(items:list[dict],field:str,out:str)->None:
 order=sorted(range(len(items)),key=lambda i:items[i][field]);previous=0
 for rank,index in enumerate(order):previous=max(previous,min(1.,items[index][field]*(len(items)-rank)));items[index][out]=previous

def write_csv(path:Path,rows:list[dict])->None:
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main()->None:
 assert (ROOT/'formal.rc').read_text().strip()=='0', 'formal device workflow did not finish successfully'
 strong=json.loads((ROOT/'STRONG-ADDRESS-GATES.json').read_text());assert strong['status']=='PASS' and strong['gate_cases']==594 and strong['timing_binary_unchanged']
 out=ROOT/'analysis-output';out.mkdir(exist_ok=True)
 rows=read_stage('stage3');assert len(rows)==216*20
 (out/'stage3-raw-observations.json').write_text(json.dumps(rows,indent=2))
 by={}
 for r in rows:by.setdefault(r['case'],{})[r['block']]=r
 assert len(by)==216 and all(set(v)==set(range(20)) for v in by.values())
 summary=[];contrasts=[];reorder=[]
 for name,data in sorted(by.items()):
  v=[float(data[b]['us_per_matrix']) for b in range(20)];q=interval(v);summary.append(dict(case=name,**{k:v for k,v in q.items() if k!='values'},working_set_bytes=int(data[0]['working_set_bytes']),pool_bytes=int(data[0]['source_pool_bytes']),api_per_core=int(data[0]['api_calls'])))
  if name.endswith('-p0'):
   for p in [1,2]:
    other=name[:-1]+str(p);r=pair([float(by[other][b]['us_per_matrix']) for b in range(20)],v);contrasts.append(dict(case=other,baseline=name,primary=name.startswith('cora-B1-') and ('-n128-' in name or '-n256-' in name),**r))
  if name.startswith('cora-B0-'):
   b1=name.replace('cora-B0-','cora-B1-');r=pair(v,[float(by[b1][b]['us_per_matrix']) for b in range(20)]);reorder.append(dict(case=name,baseline=b1,**r))
 primary=[r for r in contrasts if r['primary']];assert len(primary)==16
 holm(primary,'sign_p','primary_holm_sign_p');holm(contrasts,'sign_p','exploratory_holm_sign_p')
 r_sensitivity=[]
 for name,data in sorted(by.items()):
  if name.startswith('synthetic-r1-'):
   first=[float(data[b]['us_per_matrix']) for b in range(20)]
   for r in [4,16,64]:
    other=name.replace('synthetic-r1-',f'synthetic-r{r}-');r_sensitivity.append(dict(case=other,baseline=name,**pair([float(by[other][b]['us_per_matrix']) for b in range(20)],first)))
 (out/'R-sensitivity.json').write_text(json.dumps(r_sensitivity,indent=2))
 (out/'paired-contrasts.json').write_text(json.dumps(contrasts,indent=2));(out/'reordering-ratios.json').write_text(json.dumps(reorder,indent=2));write_csv(out/'stage3-summary.csv',summary)
 micro_records=[];micro_curves=[]
 for stage,mode in [('stage2',0),('a-micro',1),('a-micro',2)]:
  source=read_stage(stage,mode);expected=2000 if stage=='stage2' else 40;assert len(source)==expected*20
  curves={}
  for r in source:
   name,batch=r['case'].rsplit('-b',1);curves.setdefault((name,r['block']),[]).append((int(batch),float(r['us'])))
  fits={}
  for (name,block),points in curves.items():
   points=sorted(points);assert [p[0] for p in points]==[64,256,1024,4096]
   x=np.array([p[0] for p in points]);y=np.array([p[1] for p in points]);coef=np.polyfit(x,y,1);pred=np.polyval(coef,x);r2=float(1-np.sum((pred-y)**2)/np.sum((y-y.mean())**2))
   micro_curves.append(dict(stage=stage,a_mode=mode,case=name,block=block,k_us=float(coef[0]),intercept_us=float(coef[1]),r2=r2,raw_points=points));fits.setdefault(name,[]).append((block,float(coef[0]),r2))
  for name,fit in sorted(fits.items()):
   fit=sorted(fit);assert [p[0] for p in fit]==list(range(20));q=interval([p[1] for p in fit]);es=4 if '-FP32-' in name else 2;n=int(re.search(r'-n(\d+)',name).group(1));h=int(re.search(r'-h(\d+)',name).group(1)) if '-h' in name else 16
   if name.startswith('micro-copy-'):
    path=int(re.search(r'-p(\d+)',name).group(1));calls=1 if path==0 else h if path==1 else n//(32//es);counter='B DataCopy API calls'
   elif stage=='a-micro':calls=2 if mode==1 or es==2 else 3;counter='complete A-chain iterations; legacy api_calls is not total API count'
   else:calls=1;counter='B LoadData API calls (plain and transpose have different layout semantics)'
   micro_records.append(dict(stage=stage,a_mode=mode,case=name,payload_bytes=256*es if stage=='a-micro' else h*n*es,API_calls_per_payload=calls,raw_counter_unit=counter,min_r2=min(p[2] for p in fit),mean_r2=statistics.mean(p[2] for p in fit),**q))
 a_pairs=[]
 for name in sorted({r['case'] for r in micro_records if r['stage']=='a-micro'}):
  first=next(r for r in micro_records if r['stage']=='a-micro' and r['a_mode']==1 and r['case']==name)
  second=next(r for r in micro_records if r['stage']=='a-micro' and r['a_mode']==2 and r['case']==name)
  assert all(json.loads((ROOT/f'results-a-micro-a1/b{b:02}-accepted.json').read_text())['paired_block'] for b in range(20))
  assert all(json.loads((ROOT/f'results-a-micro-a2/b{b:02}-accepted.json').read_text())['paired_block'] for b in range(20))
  a_pairs.append(dict(case=name,ordinary_over_nd=pair(second['values'],first['values'])))
 holm([r['ordinary_over_nd'] for r in a_pairs],'sign_p','holm_sign_p')
 (out/'A-chain-paired-contrasts.json').write_text(json.dumps(a_pairs,indent=2))
 (out/'micro-fits.json').write_text(json.dumps(micro_records,indent=2));(out/'micro-per-block-fits.json').write_text(json.dumps(micro_curves,indent=2))
 winners=[]
 for nd in sorted(set(r['baseline'] for r in primary)):
  options=[r for r in primary if r['baseline']==nd];chosen=min(options,key=lambda r:r['first_mean_us']);winners.append(dict(baseline=nd,chosen=chosen['case'],mean_ratio=chosen['ratio_of_means'],mean_paired_ratio=chosen['ratio']['mean'],descriptive_over20=chosen['ratio_of_means']<.8,ci_upper_below_08=chosen['ratio_of_means_paired_bootstrap_ci95'][1]<.8))
 decision=dict(primary_cells=8,strict_majority=5,descriptive_over20_count=sum(r['descriptive_over20'] for r in winners),pointwise_ci_over20_count=sum(r['ci_upper_below_08'] for r in winners),winners=winners,selection='Exploratory min of two means; both paired intervals retained; no selection-adjusted CI claim.')
 (out/'decision.json').write_text(json.dumps(decision,indent=2))
 lines=['# M11 配对计时分析','','独立重复单位为20个随机时间区组；窗口和核不是独立样本。主格8个，严格多数5/8；普通两条路径分别保留配对数据，不将最小均值当无偏选优。',f"描述性时间下降超过20%的主格：{decision['descriptive_over20_count']}/8。点置信区间上界仍低于0.8的主格：{decision['pointwise_ci_over20_count']}/8。",'','| Cora B1主格 | 普通路径 | 平均耗时比 | 配对bootstrap95%CI | 时间下降 | 主族Holm符号检验p |','|---|---|---|---|---|---|']
 for r in primary:
  q=r['ratio'];lines.append(f"| {r['baseline']} | {r['case'][-2:]} | {r['ratio_of_means']:.6f} | [{r['ratio_of_means_paired_bootstrap_ci95'][0]:.6f}, {r['ratio_of_means_paired_bootstrap_ci95'][1]:.6f}] | {r['time_drop_pct']:.2f}% | {r['primary_holm_sign_p']:.6g} |")
 lines+=['','每条路径的全部20轮、主机分配/唯一选中工作集、API次数、原始makespan见JSON和CSV。普通路径B0/B1比另见reordering-ratios.json。', '', '## Claim Candidates','','- Claim: 测试范围内三种B供数链与CPU参考相符；FP32原始A普通stride重排链与ND2NZ链相符。','  - Source evidence: GATES-PASSED.json 与实际输出哈希。','  - Allowed wording: 限定有限整数标记、Cora真实窗口与固定稠密A消费。','  - Forbidden stronger wording: 任意浮点位模式正确，或完整稀疏端到端SpMM已验收。','  - Uncertainty: 仅Cora及本合成网格。','  - Next check: 外部矩阵和完整真实稀疏A消费由后续研究决定。','  - Decision: keep']
 (out/'analysis-report.md').write_text('\n'.join(lines)+'\n')
 (out/'stats-appendix.md').write_text('''# 统计口径\n\n- 所有有效样本完整保留；不按输赢、异常值或拟合R²事后删点。\n- 单配置均值、样本SD与t(19)点95%CI；配对效果为每区组的普通/ND比，并单独报告时间下降、ratio of means加速比、差值和dz。\n- 符号检验为主假设检验（配对方向，允许非正态；仍依赖区组交换性）。主族16比较Holm校正；全探索族144比较另作Holm。Shapiro、配对log t、Wilcoxon和lag1相关只作假设/敏感性记录。Shapiro不拒绝不等于证明正态。\n- 主降时判据与选路使用平均绝对耗时之比（ratio of means）；该比值的点95%CI由10000次成对区组bootstrap给出（固定seed20261115）。均值配对比、SD和t区间作为不同估计量另外保留，不能混用。\n- 20轮按时间连续，不能证明跨轮独立；哨兵、随机化与漂移登记减少但不能消除时变风险。点CI无多重区间保证。\n- 最快普通路径为事后两选一，只作描述；分别保留两条配对CI与校正p值。\n- 微基准每区组四批量拟合T=c+kB，k为整份载荷/加载链有效代价，保留截距、R²与逐点；h同时改变字节与调用，不能命名为纯固定指令开销。\n- plain加载计时只表示primitive，输入布局语义与转置不同，不能把差价直接加到端到端路径。\n- 微基准CSV里的working_set_bytes沿用通用host的副本容量记账；micro仅执行一份载荷，其实际唯一访问量为h*N*元素字节，不能将该字段当真实micro工作集。源池为64MiB。\n- cold为实际唯一选中行工作集大于4倍SDK L2(192MiB)，不能推断Cora每次访问均冷；池、跨度、累计字节分开报告。\n- 阶段3 api_calls仅计B的MTE2 DataCopy，排除加载/MMAD/写回；A微基准的同名raw字段计整条LoadA链迭代，不能冒充其内部2/3个API调用；派生表逐项给出API_calls_per_payload与counter单位。\n- 原始manifest的source_span_rows描述字段未同步源副本步长调整，多记16行；实际kernel/host使用config[12]，工作集审计和CSV按实际步长计算。该描述字段不参与测量或统计，报告以config与CSV为准。\n- 按行路径调用数固定，并不证明物理连续性/段数对时间无影响；R-sensitivity.json保留U64下R变化的配对结果，cold实际工作集按各格实报。\n- 核计时按M4的50ticks/μs换算，全卡makespan归一化为吞吐，非孤立核/单条指令延迟。\n''')
 from finalize_analysis import finalize
 finalize(ROOT)
 print(json.dumps(decision,indent=2))
if __name__=='__main__':main()
