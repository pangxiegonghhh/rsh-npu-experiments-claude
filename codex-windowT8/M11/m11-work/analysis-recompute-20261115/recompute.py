"""R1–R12: read immutable M11 evidence and write only this new directory."""
from pathlib import Path
import csv, json, struct, hashlib, math
import numpy as np
from scipy import stats

OUT = Path(__file__).resolve().parent
WORK = OUT.parent
RAW = WORK / 'recovered-evidence'
OLD = RAW / 'analysis-output'
SOURCE = WORK.parent / 'codex-windowT8'

def load(p: Path): return json.loads(p.read_text())
def words(p: Path):
    raw = p.read_bytes()
    return list(struct.unpack('<'+'I'*(len(raw)//4), raw))
def csvout(name, rows):
    assert rows
    with (OUT/name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
def table(rows, keys=None):
    keys = keys or list(rows[0])
    def fmt(x): return f'{x:.6f}' if isinstance(x,float) else str(x)
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r[k]) for k in keys)+' |' for r in rows])
def md(num, text): (OUT/f'R{num}.md').write_text(f'# R{num}\n\n'+text+'\n')
def effect(x, y):
    x,y=np.array(x),np.array(y);assert len(x)==len(y)==20
    rng=np.random.default_rng(20261115);ix=rng.integers(0,20,size=(10000,20))
    boot=x[ix].mean(axis=1)/y[ix].mean(axis=1)
    ratio=float(x.mean()/y.mean())
    return dict(ratio=ratio,ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),time_drop_pct=100*(1-ratio))
def stage(stage='stage3',mode=0):
    result={}
    for f in sorted((RAW/f'results-{stage}-a{mode}').glob('b*-accepted.json')):
        reg=load(f);assert reg['valid'];block=reg['block']
        for row in csv.DictReader((RAW/reg['path']/'timing.csv').open()):
            row['folder']=RAW/reg['path']/row['case']
            result.setdefault(row['case'],{})[block]=row
    assert all(set(v)==set(range(20)) for v in result.values())
    return result

def main():
    data=stage();assert len(data)==216
    manifest=load(RAW/'manifest.json');assert len(manifest)==306
    by={r['name']:r for r in manifest}
    csvout('cases.csv',[dict(case_id=c['name'],stage='gate-only' if c['gate_only'] else 'stage3',**{k:v for k,v in c.items() if k!='name'}) for c in manifest])
    mean={k:float(np.mean([float(v[b]['us_per_matrix']) for b in range(20)])) for k,v in data.items()}
    sd={k:float(np.std([float(v[b]['us_per_matrix']) for b in range(20)],ddof=1)) for k,v in data.items()}
    def values(name): return [float(data[name][b]['us_per_matrix']) for b in range(20)]
    # R1: raw clocks, replay-count denominator and complete 20-block example.
    name='cora-B1-FP32-n256-cold-p0';r1=[]
    for b,r in sorted(data[name].items()):
        st=words(r['folder']/'stats.bin');starts=[st[i*32]+(st[i*32+1]<<32) for i in range(24)];ends=[st[i*32+2]+(st[i*32+3]<<32) for i in range(24)]
        ticks=max(ends)-min(starts);us=ticks/50;replays=int(r['cycles'])*int(r['blocks']);v=us/replays
        assert math.isclose(v,float(r['us_per_matrix']),rel_tol=1e-10)
        r1.append(dict(block=b,min_begin_tick=min(starts),max_end_tick=max(ends),elapsed_ticks=ticks,elapsed_us=us,replay_repeats_per_core=int(r['cycles']),cores=24,windows_per_replay=170,completed_replays=replays,us_per_replay=v,us_per_window=v/170))
    csvout('R1-example.csv',r1);q=r1[0];m=float(np.mean([r['us_per_replay'] for r in r1]))
    assert round(m,4)==12.5942
    md(1,f'''**原报告“μs/矩阵”标签不精确，应改为“μs/完整回放副本”的吞吐归一化。`cycles`是外层回放重复次数，单位为次，不是时钟周期。**

归一化计算的数值与量纲可以成立（分母cycles单位是次），并非原时钟除法算错；应纠正的是字段解释与Cora“每矩阵”标签。

公式：T_replay = (max_c end_c − min_c begin_c) / (50 ticks/μs) / (E × C)。E=host字段cycles，C=24核；每核独立执行E份完整行列表。Cora每份含W=170窗口；真正窗口归一化为T_window=T_replay/170。合成每份W=1，因此两个指标同值。分母没有内层tile数T，E×24也没有乘170，不能把12.5942叫单窗延迟。

block0例：({q['max_end_tick']}−{q['min_begin_tick']})/50 = {q['elapsed_us']:.6f} μs；E={q['replay_repeats_per_core']}，C=24，完成{q['completed_replays']}份回放，得到{q['us_per_replay']:.9f} μs/回放（{q['us_per_window']:.9f} μs/窗口）。**单block不等于20轮均值**；R1-example.csv列全部20轮，平均={m:.9f}→12.5942，匹配原summary。原高N同格路径/冷热/B0B1比值不受共同分母影响；合成与Cora绝对“每矩阵”值不可直接互比。

依据：原host.cpp Run::cycles、cfg[5]/cfg[6]与CSV除式，kernel.cpp total=cycles*tiles；原始stats.bin。没有改原报告/数据。''')
    # R2: all existing block/core observations; no fictional repetitions.
    names=[f'cora-B1-{d}-n{n}-{cache}-p{p}' for d,n,p in [('FP16',128,1),('FP16',128,0),('FP16',256,1),('FP32',128,1)] for cache in ['hot','cold']]
    detail=[]
    for name in names:
        cfg=words(RAW/'inputs'/(name+'.config.bin'));es=4 if cfg[0] else 2;n=cfg[1];path=cfg[8]
        for b,r in sorted(data[name].items()):
            st=words(r['folder']/'stats.bin');E=int(r['cycles']);expected=E*cfg[17]
            for core in range(int(r['blocks'])):
                s=st[core*32:(core+1)*32];begin=s[0]+(s[1]<<32);end=s[2]+(s[3]<<32)
                assert s[4]==int(r['api_calls'])==expected
                detail.append(dict(case_id=name,block=b,rep='single_saved_measurement',core=core,begin_tick=begin,end_tick=end,elapsed_ns=(end-begin)*20,api_calls_actual=s[4],api_calls_expected=expected,calls_per_replay=cfg[17],bytes_moved_measured='NOT_RECORDED',requested_B_bytes_derived=E*cfg[2]*16*n*es,blockCount=n//(32//es) if path==1 else 'ND2NZ',blockLen=1 if path==1 else 'NA',srcStride=0 if path==1 else 'NA',dstStride=15 if path==1 else 'NA',descriptor_provenance='source+config; no runtime descriptor trace',elapsed_full_card_us=float(r['us']),us_per_replay=float(r['us_per_matrix'])))
    csvout('R2-raw-core-observations.csv',detail)
    micro=load(OLD/'micro-fits.json');comparison=[]
    for d,n in [('FP16',128),('FP16',256),('FP32',128),('FP32',256)]:
        fit=next(r for r in micro if r['case']==f'micro-copy-{d}-n{n}-h1-p1')
        fit16=next(r for r in micro if r['case']==f'micro-copy-{d}-n{n}-h16-p1')
        pred=fit16['mean']*7280/16/24
        comparison.append(dict(dtype=d,N=n,blockCount=n//(16 if d=='FP16' else 8),micro_h1_k_us=fit['mean'],micro_h16_k_us=fit16['mean'],h16_amortized_per_row_us=fit16['mean']/16,review_amortized_prediction_us=pred,h1_naive_prediction_us=fit['mean']*7280/24,hot_us_per_replay=mean[f'cora-B1-{d}-n{n}-hot-p1'],cold_us_per_replay=mean[f'cora-B1-{d}-n{n}-cold-p1'],cold_over_review_prediction=mean[f'cora-B1-{d}-n{n}-cold-p1']/pred))
    csvout('R2-comparison.csv',comparison)
    md(2,'''**判断（c）：现有数据分不开，不能确认测量故障，也不能认定blockCount=8的硬件几何惩罚。** 不剔除格，预登记分母保持8。

R2-raw-core-observations.csv保留8个指定对照配置×20区组×24核=3840行。原实验每格每区组为1次预热+1次保存计时，并没有20×20个rep；未保存的rep和bytes_moved硬件读数标明缺失，不伪造。按行每完整B1回放7280次API，每核原计数为7280×E；全部核匹配。elapsed_ns由原begin/end按20ns/tick换算；字节列是描述符请求字节的推导，非实际HBM/总线字节计数。描述符四元组来自固定源码/config，不能冒充运行时trace。

''' + table(comparison) + '''

同精度N256比N128快的非单调现象在两档都稳定；但阶段2同blockCount采用单核、每载荷强制等待，阶段3是24核、共同gmax、双bank/消费流水和不同访存布局，未对这些因素控制。没有PMU/descriptor trace或同流水blockCount扫参，因此阶段2不重现不排除几何与流水交互，也无法证明该机制。审核给出的4.42/4.99/4.97/7.64来自h16整体代价先除16再乘7280/24，是h16摊销到每行的预测，并非真正h1单行斜率。表中同时列出真实h1与h16摊销两种口径；真实h1直接外推约36–41 μs，四格都不匹配。朴素calls模型不是已验证性能模型，审核的2.90倍偏差只在特定摊销假设下成立，不能当故障检验。''')
    # R3: all 108 actual cold/hot pairs, plus the 12 primary pairs.
    coldhot=[];access=[]
    for name in sorted(data):
        if '-cold-' not in name: continue
        hot=name.replace('-cold-','-hot-');cfg=words(RAW/'inputs'/(name+'.config.bin'));rr=words(RAW/'inputs'/(name+'.rows.bin'));selected={r for r in rr if r<0xffffff00};n=cfg[1];es=4 if cfg[0] else 2
        primary=name.startswith('cora-B1-') and n>=128
        coldhot.append(dict(case_id=name,hot_case=hot,primary=primary,**effect(values(name),values(hot))))
        r=data[name][0];E=int(r['cycles']);cores=int(r['blocks']);replicas=int(r['replicas']);visited=min(replicas,E*cores)
        unique=visited*len(selected)*n*es
        assert unique==int(r['working_set_bytes']) and unique>=4*192*1024**2
        access.append(dict(case_id=name,unique_logical_rows_per_replica=len(selected),allocated_replicas=replicas,visited_replicas=visited,unique_nonzero_rows_visited=visited*len(selected),unique_selected_bytes=unique,L2_bytes=192*1024**2,at_least_4L2=unique>=4*192*1024**2,requested_B_bytes_per_core=E*cfg[2]*16*n*es,requested_B_bytes_total=E*cfg[2]*16*n*es*cores,actual_HBM_bytes='NOT_MEASURED',basis='config row IDs + audited bases generation + clocks/counters; no address trace'))
    assert len(coldhot)==len(access)==108
    csvout('R3-all-cold-hot.csv',coldhot);csvout('R3-cold-access.csv',access)
    pp=[r for r in coldhot if r['primary']];assert len(pp)==12
    csvout('R3-primary-cold-hot.csv',pp)
    md(3,'''**按行cold确实覆盖≥4×L2的唯一选中数据（基于已审计地址/实际副本使用数重建），但该事实不等于逐访问均为HBM冷读。** 未采集实际HBM字节/PMU命中率，不能证明发射数是瓶颈。

原216配置组成108对cold/hot；高N B1为4种精度/N×3路径=12对，并非“8格×3”的24个独立比值。8格×3=24个绝对观测条件在R6表中保留。按行两档近似等时是真实计时现象；cold格相较hot格的更大相对降幅来自ND变慢，**不是按行变快**。

''' + table(pp,['case_id','ratio','ci_low','ci_high']) + '''

R3-cold-access.csv列108个cold配置的唯一行数、实际访问副本、请求字节、唯一字节与依据。host生成bases[i]=(i%replicas)*span，i遍历E×24；visited=min(replicas,E×24)，本次全部访问满登记副本，副本span与选中行集合不重叠。零填充为共享零尾，不把间距空洞计为唯一选中数据。缺少动态地址trace及HBM计数，如实标记。''')
    # R4 and R7.
    fixed={1:[],2:[]};selection=[]
    for d in ['FP16','FP32']:
        for n in [128,256]:
            for cache in ['hot','cold']:
                base=f'cora-B1-{d}-n{n}-{cache}-p0';opts=[]
                for p in [1,2]:
                    name=base[:-1]+str(p);q=dict(case_id=name,**effect(values(name),values(base)));fixed[p].append(q);opts.append(q)
                best=min(opts,key=lambda q:q['ratio']);selection.append(dict(cell=base[:-3],chosen=best['case_id'],selected_ratio=best['ratio'],fixed_row_ratio=opts[0]['ratio'],selected_minus_fixed_row=best['ratio']-opts[0]['ratio']))
    hot=[r for r in fixed[1] if '-hot-' in r['case_id']];assert len(hot)==4 and sum(r['ratio']<.8 for r in hot)==3
    csvout('R4-hot-only-posthoc.csv',hot)
    md(4,'**【事后】hot-only下3/4格降幅≥25%，方向与原主判读一致。** 这是改变子集后的敏感性分析，不能写成“预登记判据在hot-only下也满足”。原判据保持8格，6/8；本次未剔点。\n\n'+table(hot))
    for p in [1,2]: csvout(f'R7-fixed-p{p}.csv',fixed[p])
    csvout('R7-selection-vs-fixed.csv',selection)
    md(7,'固定两条路径各8格如下。全部8格选优都选p1，选优与固定按行的差均为0；选择偏差问题仍如实保留，但不是本次六格优势由交叉拼接产生。\n\n'+table(fixed[1])+'\n\n'+table(fixed[2])+'\n\n'+table(selection))
    # R5/R6 all reordering and absolute numbers, exact cross-check.
    reorder=[];absolute=[]
    for d in ['FP16','FP32']:
        for n in [16,128,256]:
            for cache in ['hot','cold']:
                for p in range(3):
                    b0=f'cora-B0-{d}-n{n}-{cache}-p{p}';b1=b0.replace('B0','B1')
                    e=effect(values(b0),values(b1));assert math.isclose(e['ratio'],mean[b0]/mean[b1])
                    reorder.append(dict(cell=f'{d}-n{n}-{cache}',path=p,speedup_B0_over_B1=e['ratio'],ci_low=e['ci_low'],ci_high=e['ci_high'],B1_time_drop_pct=100*(1-1/e['ratio'])))
                    if n>=128:
                        absolute.append(dict(cell=f'{d}-n{n}-{cache}',path=p,B0_mean_us_per_replay=mean[b0],B0_SD=sd[b0],B1_mean_us_per_replay=mean[b1],B1_SD=sd[b1],n_blocks=20,B1_over_ND=mean[b1]/mean[b1[:-1]+'0']))
    assert len(reorder)==36 and len(absolute)==24
    csvout('R5-reordering-all-paths.csv',reorder);csvout('R6-absolute-all-paths.csv',absolute)
    wide=[]
    for cell in dict.fromkeys(r['cell'] for r in reorder):
        row={'cell':cell}
        for p in range(3):
            q=next(r for r in reorder if r['cell']==cell and r['path']==p)
            row[f'p{p}_speedup_CI_drop']=f"{q['speedup_B0_over_B1']:.6f} [{q['ci_low']:.6f},{q['ci_high']:.6f}] / {q['B1_time_drop_pct']:.3f}%"
        wide.append(row)
    md(5,'12格×3路径全部补齐；源216配置中Cora部分72配置组成36个B0/B1配对。高N除FP16/N128外，ND重排收益约1.8倍，大于按行约1.48倍；按条依配置不同，不能给全局排序。\n\n'+table(wide))
    md(6,'8个高N格×3路径×B0/B1，共48个绝对均值；下表24行每行含B0和B1。单位已纠正为μs/完整回放，20区组均值与样本SD。R5逐格由本表B0_mean/B1_mean复核一致；p2逐格比值已列。\n\n'+table(absolute))
    # R8 actual physical row runs and command merges, not generator intent.
    gaps=[];sensitivity=[];rawgap=[]
    for R in [1,4,16,64]:
        exemplar=f'synthetic-r{R}-FP16-n128-hot-p0'
        rr=[r for r in words(RAW/'inputs'/(exemplar+'.rows.bin')) if r<0xffffff00]
        runs=[]
        for row in rr:
            if runs and row==runs[-1][-1]+1:runs[-1].append(row)
            else:runs.append([row])
        gg=[runs[i+1][0]-runs[i][-1]-1 for i in range(len(runs)-1)]
        assert len(runs)==R
        rawgap.append(dict(R=R,gaps=gg,rows=rr))
        for d in ['FP16','FP32']:
            for n in [128,256]:
                base=f'synthetic-r{R}-{d}-n{n}-hot-p0';cfg=words(RAW/'inputs'/(base+'.config.bin'));off=words(RAW/'inputs'/(base+'.offsets.bin'));cmd=words(RAW/'inputs'/(base+'.commands.bin'));pieces=sum(cmd[i+2] for i in range(0,len(cmd),8));api=len(cmd)//8
                assert api==cfg[17]
                gaps.append(dict(R=R,dtype=d,N=n,gap_count=len(gg),gap_min=min(gg) if gg else 'NA',gap_p50=float(np.median(gg)) if gg else 'NA',gap_max=max(gg) if gg else 'NA',all_equal=len(set(gg))==1 if gg else 'NA',tile_pieces=pieces,ND_API_calls=api,api_over_pieces=api/pieces))
                for cache in ['hot','cold']:
                    nd=base.replace('-hot-',f'-{cache}-');row=nd[:-1]+'1'
                    sensitivity.append(dict(case_id=row,**effect(values(row),values(nd))))
    assert len(sensitivity)==32
    csvout('R8-full-sensitivity.csv',sensitivity);csvout('R8-gap-merge.csv',gaps)
    (OUT/'R8-raw-gaps.json').write_text(json.dumps(rawgap,indent=2))
    md(8,'原始实际行列表确认：R4/16/64间距为固定seed的1/2行随机序列，不是全等间距（R1无段间距，不能叫等距或随机多段）。B1设备项按补测计划自动取消。随机序列仍有局部相等，允许ND合法局部合并；不能把随机化解释成完全禁用合并。下表直接计算API/段片比例，R敏感性仍混合合并率、地址与缓存等因素，不能当纯R因果效应。\n\n'+table(gaps)+'\n\n'+table(sensitivity))
    # R9: absent PMU remains absent.
    profiler=list(RAW.rglob('*profiler*'));rows=[]
    for d in ['FP16','FP32']:
        for n in [128,256]:rows.append(dict(case_id=f'cora-B1-{d}-n{n}-hot-p0',mean_us_per_replay=mean[f'cora-B1-{d}-n{n}-hot-p0'],MTE2_pct='NOT_RECORDED',MTE1_pct='NOT_RECORDED',MMAD_pct='NOT_RECORDED',sync_pct='NOT_RECORDED',Scalar_pct='NOT_RECORDED'))
    csvout('R9-attribution-unavailable.csv',rows)
    md(9,'**现有证据无法归因。** 无profiler/PMU分项证据（归档匹配路径数='+str(len(profiler))+'），只有覆盖重叠流水的begin/end makespan，不能相加拆成五类占比，也不能推断hot基线被发射/同步/MMAD之一钉住。\n\n'+table(rows))
    # R10: paired difference and descriptor table for the existing non-equivalent primitives.
    diff=[]
    for d in ['FP16','FP32']:
        for n in [16,128,256]:
            a=next(r for r in micro if r['case']==f'micro-plain-{d}-n{n}');b=next(r for r in micro if r['case']==f'micro-transpose-{d}-n{n}');delta=np.array(b['values'])-np.array(a['values']);half=stats.t.ppf(.975,19)*delta.std(ddof=1)/np.sqrt(20)
            diff.append(dict(dtype=d,N=n,plain_repeat=16*n*(2 if d=='FP16' else 4)//512,transpose_repeat=n//16,plain_ifTranspose=False,transpose_api='LoadData(ifTranspose=true)' if d=='FP16' else 'LoadDataWithTranspose',srcStride=1,FP32_dstFracGap=n//16-1 if d=='FP32' else 'NA',delta_us=float(delta.mean()),delta_ci_low=float(delta.mean()-half),delta_ci_high=float(delta.mean()+half),annotation='non-equivalent L0 contents; cannot estimate pure transpose cost'))
    csvout('R10-primitive-descriptors.csv',diff)
    md(10,'**不能判为纯发射开销；这两列不可用于估算等价路径的转置成本。** 两者同一B1 L1源，但plain不转置且FP32重复数不同，产生不同L0B布局。原micro正确性在计时后调用Compute重新做正确转置，覆盖了计时primitive的L0B结果，所以“最终C正确”不验证plain计时结果。差价含不同描述符/指令/同步/标量控制，近似常数无法区分这些。此处新增注释表，不改原micro-fits.json。B3必须在新设备门中直接消费被测加载结果，禁止再被Compute覆盖。\n\n'+table(diff))
    # R11: distinguish ND2NZ fields from DataCopyParams rather than inventing aliases.
    achains=[dict(dtype='FP16',mode=1,API='ND2NZ',blockCount='NA',blockLen='NA',srcStride='NA',dstStride='NA',ndNum=1,nValue=16,dValue=16,srcDValue=16,dstNzC0Stride=16,dstNzNStride=1,copy_calls=1,payload_bytes=512,load_repeat=1,load_srcStride=1,load_dstGap=0),dict(dtype='FP16',mode=2,API='DataCopy(length=256)',blockCount='length overload',blockLen='16 blocks equivalent',srcStride=0,dstStride=0,ndNum='NA',nValue='NA',dValue='NA',srcDValue='NA',dstNzC0Stride='NA',dstNzNStride='NA',copy_calls=1,payload_bytes=512,load_repeat=1,load_srcStride=1,load_dstGap=0),dict(dtype='FP32',mode=1,API='ND2NZ',blockCount='NA',blockLen='NA',srcStride='NA',dstStride='NA',ndNum=1,nValue=16,dValue=16,srcDValue=16,dstNzC0Stride=16,dstNzNStride=1,copy_calls=1,payload_bytes=1024,load_repeat=1,load_srcStride=1,load_dstGap=1),dict(dtype='FP32',mode=2,API='DataCopy twice: dst0/src0, dst128/src8 floats',blockCount=16,blockLen=1,srcStride=1,dstStride=0,ndNum='NA',nValue='NA',dValue='NA',srcDValue='NA',dstNzC0Stride='NA',dstNzNStride='NA',copy_calls=2,payload_bytes=1024,load_repeat=1,load_srcStride=1,load_dstGap=1)]
    csvout('R11-A-descriptors.csv',achains)
    ap=[]
    for mode in [1,2]:
        for f in sorted((RAW/f'results-a-micro-a{mode}').glob('b*-accepted.json')):
            q=load(f);assert q['paired_block']
            sample=next(csv.DictReader((RAW/q['path']/'timing.csv').open()));assert int(sample['a_mode'])==mode
            ap.append(dict(mode=mode,block=q['block'],recorded_a_mode=sample['a_mode'],path=q['path']))
    csvout('R11-label-provenance.csv',ap)
    md(11,'**未发现标签对调；命令参数→host cfg[13]→kernel aMode分支→CSV a_mode四者一致。** 原两组共享20区组、记录的a_mode均匹配。两种物理布局均通过独立强地址门。不能仅凭≈0.78/≈0.13互换推定对调。\n\n'+table(achains)+'''\n\nFP16为512B、一个16×16 fractal；FP32为1024B、两个32B块宽的半幅，普通链需两条16-block stride拷贝，源偏移0/8 floats、目的0/128 floats。ND2NZ的参数不能冒充普通blockCount四元组。LoadDataWithTranspose FP32 dstGap=1匹配不同L0A放置。几何/stride差异解释了“这不是同一载荷描述符”的事实，但**不能仅用几何证明5.5倍的具体时间机制**；无PMU或几何单变量扫参，因果归因仍答不了。''')
    # R12 complete requested 54-cell mapping.
    gates=load(RAW/'GATES-PASSED.json');paths={r['gate'] for r in gates['records']};cover=[]
    for d in ['FP16','FP32']:
        for n in [16,128,256]:
            for h in [1,4,16]:
                for p in range(3):
                    name=f'gate-h{h}-{d}-n{n}-hot-p{p}';path=f'gate-v1/{name}/gate.json';assert path in paths
                    y=(RAW/'gate-v1'/name/'output-f32.bin').read_bytes();ref=(RAW/'gate-v1'/name/'reference-f32.bin').read_bytes();assert y==ref
                    cover.append(dict(dtype=d,N=n,segment_length=h,path=p,status='COVERED',initial_gate=path,strong_gate=f'gate-address-a0/full-address-{name}/gate.json',output_sha256=hashlib.sha256(y).hexdigest()))
    assert len(cover)==54
    csvout('R12-coverage-54.csv',cover)
    md(12,'**54/54格均已覆盖，不需执行binary或新增设备门。** 每个gate-hh含两段长度h的非连续行，另含尾部零填充；初始门完整输出与CPU参考逐字节一致，已重新读取核对。54行逐格映射见CSV。\n\n198=11种geometry×2精度×3N×3路径；11种为4合成R+2 Cora+3段长门+tail+stride。不是198个独立统计重复。三种A模式各198，加micro510，共1104；强地址门另198×3=594且时序在计时后。原文“host check不占设备”不正确：原host调用ACL/NPU；本项仅复核已保存输出，不运行host check。\n\n'+table(cover,['dtype','N','segment_length','path','status','initial_gate']))
    # Recheck frozen files and emit manifest last.
    baseline=load(OUT/'ORIGINAL-BASELINE-SHA256.json')
    baseline_checked=0;unshipped_baselines=[]
    for path,digest in baseline.items():
        marker='/m11-work/';relative=path.split(marker,1)[1] if marker in path else None
        candidate=WORK/relative if relative else Path(path)
        if candidate.is_file():
            assert hashlib.sha256(candidate.read_bytes()).hexdigest()==digest,path;baseline_checked+=1
        else:unshipped_baselines.append(path)
    # Full device tar is deliberately not duplicated in Git. Its SHA is registered separately.
    assert all(name.endswith('m11-evidence-complete.tar.gz') for name in unshipped_baselines),unshipped_baselines
    status=[dict(item=f'R{i}',status='DONE',limitation='mechanism unavailable' if i in [2,9,10,11] else '') for i in range(1,13)]
    csvout('status.csv',status)
    (OUT/'README.md').write_text('''# M11 独立重算交付 / 2026-11-15

R1–R12均已处理；不能归因的项如实写明，未伪造PMU/trace/rep。所有产物位于本新目录，原tar、原analysis-output、原报告哈希不变。所有306原配置在cases.csv中登记；216阶段3配置完整保留，20时间区组；54/54正确性网格覆盖。

最重要更正：原“μs/矩阵”是μs/完整回放（Cora一份170窗口），不是单窗延迟。配置内的比值与6/8描述性主判读不变。R2判(c)，不剔格。R3按已审计实际地址重建，cold按行确实覆盖≥4×L2唯一字节，但没有PMU命中证据；cold的更大相对降幅来自ND变慢。R4 hot-only为【事后】3/4，不冒充预登记。

偏离/缺失：原无cases.csv，本目录由原manifest生成适配清单；R2原无20×20rep与硬件bytes_moved字段；R3 8个缓存条件只能组成4种dtype/N对，每路径共12对，完整108对均交付；没有profiler；R10旧门覆盖了被测L0结果，原primitive不能做等价成本估计；R11标签无对调但具体时差机制未知；原host check需要NPU，离线只读已有输出。原始证据一律不修改。

B1阶段0已确认R4/16/64随机1/2行间距，按M11b计划自动取消设备项；分布/局部合并见R8。B2的hot/共享gmax独立补测已完成，B3直接消费门证实plain-only不等价；见../../m11b-work/2026-11-16--t8--r11b--recompute-and-bridge.md。本目录仍只含离线重算。

本重算不请求改论文/冻结结构，不按故障猜测改分母。尚需用户最终决定的论文取舍保持原样。

复现：python3 recompute.py。输出目录固定为本文件所在新目录，代码只读取原数据。SHA256SUMS覆盖本目录交付文件（自身除外）。
''')
    from render_recompute import render
    render(OUT)
    sums=[]
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name!='SHA256SUMS' and '__pycache__' not in p.parts:sums.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT)))
    (OUT/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
    print(json.dumps(dict(status='PASS',stage3_cases=216,all_cases=306,R2_core_rows=len(detail),cold_hot_pairs=108,coverage_cells=54,published_baseline_files_checked=baseline_checked,unshipped_full_mirror_files=len(unshipped_baselines))))

if __name__=='__main__':main()
