"""Block-paired M8 statistics, registered planes, and readable Markdown."""
from pathlib import Path
import csv,json,statistics as S,random,math,hashlib
p=Path(__file__).resolve().parent
def quantile(v,q):
    v=sorted(v);a=(len(v)-1)*q;i=int(a);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(a-i)
def ci(v,rng):
    values=[S.mean(rng.choices(v,k=len(v))) for _ in range(2000)];return [quantile(values,.025),quantile(values,.975)]
def ols(x,y):
    a=[[sum(row[i]*row[j] for row in x) for j in range(3)]+[sum(row[i]*v for row,v in zip(x,y))] for i in range(3)]
    for i in range(3):
        pivot=max(range(i,3),key=lambda j:abs(a[j][i]));a[i],a[pivot]=a[pivot],a[i]
        assert abs(a[i][i])>1e-12
        z=a[i][i];a[i]=[q/z for q in a[i]]
        for j in range(3):
            if j!=i:
                z=a[j][i];a[j]=[u-z*v for u,v in zip(a[j],a[i])]
    return [row[-1] for row in a]
def main():
    manifest=json.loads((p/'manifest.json').read_text());m={q['name']:q for q in manifest};obs={name:{} for name in m};journals=sorted((p/'blocks').glob('b*-accepted.json'));assert len(journals)==20
    allrows=[];drifts=[]
    for journal in journals:
        data=json.loads(journal.read_text());b=data['block']
        for group in data['groups']:
            drifts.append(group['drift'])
            for row in csv.DictReader((p/group['path']/'timing.csv').open()):
                mm=m[row['case']]
                if (mm['dtype'],mm['n'])!=(group['dtype'],group['N']):continue
                assert b not in obs[row['case']];obs[row['case']][b]=row;allrows.append(row)
    assert len(allrows)==840*20
    with (p/'timing-observations.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(allrows[0]));w.writeheader();w.writerows(sorted(allrows,key=lambda x:(x['case'],int(x['block']))))
    rng=random.Random(20261115);stats={}
    for name,v in obs.items():
        assert set(v)==set(range(20));vv=[v[b] for b in range(20)];values=[float(row['us_per_window']) for row in vv]
        stats[name]=dict(mean=S.mean(values),median=S.median(values),q25=quantile(values,.25),q75=quantile(values,.75),ci95=ci(values,rng),values=values,global_us=[float(row['us']) for row in vv],event_us=[float(row['event_us']) for row in vv],reader_us_per_window=[float(row['reader_us_sum'])/int(row['windows']) for row in vv],pack_us_per_window=[float(row['pack_us_sum'])/int(row['windows']) for row in vv],batch={k:v for k,v in vv[0].items() if k in ['windows_per_core','blocks','windows','tiles','pack_row_calls']})
    pairs=[]
    for name,mm in m.items():
        if mm['path']!='pack':continue
        for path in ['split','merge']:
            other=name[:-4]+path;a=stats[other]['values'];b=stats[name]['values'];delta=[y-x for x,y in zip(a,b)];interval=ci(delta,rng)
            pairs.append(dict(tag=mm['tag'],dtype=mm['dtype'],n=mm['n'],cache=mm['cache'],direct=path,pack=name,other=other,pack_minus_direct_mean_us=S.mean(delta),delta_ci95=interval,pack_speedup_direct_over_pack=S.mean(a)/S.mean(b),winner='direct' if interval[0]>0 else 'pack' if interval[1]<0 else 'uncertain'))
    fits=[]
    for dt in [0,1]:
     for n in [16,32,64,128,256]:
      for cache in ['hot','cold']:
       for path in ['split','merge','pack']:
        cases=[mm for mm in manifest if mm['dtype']==dt and mm['n']==n and mm['cache']==cache and mm['path']==path and not mm['tag'].startswith('cora')];assert len(cases)==12
        x=[[1,mm['u'],mm['r']] for mm in cases];coefs=[];quality=[]
        for b in range(20):
            y=[stats[mm['name']]['values'][b] for mm in cases];coef=ols(x,y);coefs.append(coef);pred=[sum(a*c for a,c in zip(row,coef)) for row in x];ss=sum((v-S.mean(y))**2 for v in y);r2=1-sum((v-q)**2 for v,q in zip(y,pred))/ss if ss else 0;err=max(abs(v-q)/v for v,q in zip(y,pred));quality.append(dict(r2=r2,max_relative_error=err))
        mean=[S.mean(row[i] for row in coefs) for i in range(3)];bounds=[ci([row[i] for row in coefs],rng) for i in range(3)]
        fit=dict(dtype=dt,n=n,cache=cache,path=path,mean=mean,ci95=bounds,block_coefficients=coefs,quality=quality,qualified=all(q['r2']>=.95 and q['max_relative_error']<=.15 for q in quality));fits.append(fit)
    boundaries=[]
    for dt in [0,1]:
     for n in [16,32,64,128,256]:
      for cache in ['hot','cold']:
       for path in ['split','merge']:
        get=lambda route:next(q for q in fits if (q['dtype'],q['n'],q['cache'],q['path'])==(dt,n,cache,route))
        a=get(path);b=get('pack');coeffs=[[y-x for x,y in zip(aa,bb)] for aa,bb in zip(a['block_coefficients'],b['block_coefficients'])]
        mean=[S.mean(q[i] for q in coeffs) for i in range(3)];bounds=[ci([q[i] for q in coeffs],rng) for i in range(3)]
        subset=[q for q in pairs if (q['dtype'],q['n'],q['cache'],q['direct'])==(dt,n,cache,path) and not q['tag'].startswith('cora')]
        winner='direct_all_grid' if all(q['winner']=='direct' for q in subset) else 'pack_all_grid' if all(q['winner']=='pack' for q in subset) else 'mixed_or_uncertain'
        boundaries.append(dict(dtype=dt,n=n,cache=cache,direct=path,difference_plane=mean,ci95=bounds,qualified=a['qualified'] and b['qualified'],grid_result=winner,block_difference_coefficients=coeffs))
    result=dict(status='PASS',accepted_blocks=20,cases=840,observations=len(allrows),max_drift=max(drifts),statistics=stats,pairs=pairs,fits=fits,boundaries=boundaries)
    (p/'analysis.json').write_text(json.dumps(result,indent=2))
    lines=['# T8 M8：直接读与 AIV 打包后读的实测报告','',f'840 配置 ×20 随机区组，共 {len(allrows):,} 条有效记录。最大哨兵漂移 {max(drifts):.3%}。','',
    '本轮是单 GM 槽串行 READY/ACK 实现；M1 未验收，不含生产消费重叠收益。直接读和槽读取采用相同双 L1 槽预取、identity MMAD 消费。AIV 每行搬运，按 16 行写 GM。包含 Scalar、同步、搬运及 MMAD，排除启动和初始 A 装载；不是纯 MTE2 busy 或完整 SpMM。','',
    '主表 us/窗口=全卡最早开始到最晚结束的设备区间 / 全卡窗口数，表示吞吐归一化时间，不等于单核心单窗口延迟。分项为各核心阶段累积 / 总窗口，不能直接相加替代全卡 makespan。原始完整内核 ACL event 时间另存 CSV。','',
    'B 实分配 2 GiB；hot 有效唯一行集合≤32 MiB，cold >4×192 MiB。GM 单槽为每组最大窗口补齐大小，可驻留 L2；Cora 保留矩阵内行复用。各配置精确字节量见 manifest。','',
    '正确性：48 个单核边界点、48 个全卡压力点及 840 个全卡配置先于正式计时。identity 消费导出全部 tile，CPU 原始行列表逐元素精确比较；FP16 转 FP32 对本轮整数标记无损。GM 槽末态、元数据、B 全池及哨兵检查；不把末态检查说成每一次迭代均导出。','',
    '配对差 CI 为固定 seed 的 2000 次区组 bootstrap。加速比=直接读均值/pack 均值，>1 表示 pack 更快。平面必须全部区组 R²≥0.95 且最大误差≤15% 才解释交线；未达标仅保留描述系数。','',
    '## 网格胜负与平面资格','', '|精度|N|缓存|直接路径|网格结果|平面合格|Δc(us)|Δa(us/U)|Δb(us/R)|','|---|---:|---|---|---|---|---:|---:|---:|']
    for q in boundaries:lines.append('|'+ '|'.join(map(str,[['FP16','FP32'][q['dtype']],q['n'],q['cache'],q['direct'],q['grid_result'],q['qualified'],*[f'{x:.8g}' for x in q['difference_plane']]]))+'|')
    lines+=['','## 全部配对结果','', '|结构|精度|N|缓存|直接路径|直接 us/窗口|pack us/窗口|直接/pack|pack−直接的95%CI(us)|判定|','|---|---|---:|---|---|---:|---:|---:|---|---|']
    for q in pairs:lines.append('|'+ '|'.join(map(str,[q['tag'],['FP16','FP32'][q['dtype']],q['n'],q['cache'],q['direct'],f"{stats[q['other']]['mean']:.8g}",f"{stats[q['pack']]['mean']:.8g}",f"{q['pack_speedup_direct_over_pack']:.5f}",f"[{q['delta_ci95'][0]:.8g}, {q['delta_ci95'][1]:.8g}]",q['winner']]))+'|')
    lines+=['','## 每配置20次原始归一化值','', '|配置|均值(us/窗口)|IQR|20轮原始值(us/窗口)|','|---|---:|---:|---|']
    for name,q in stats.items():lines.append(f"|{name}|{q['mean']:.9g}|{q['q75']-q['q25']:.8g}|"+', '.join(f'{v:.9g}' for v in q['values'])+'|')
    (p/'M8-results-20261115.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(status='PASS',cases=840,observations=len(allrows),pair_winners={s:sum(q['winner']==s for q in pairs) for s in ['direct','pack','uncertain']},qualified_planes=sum(q['qualified'] for q in fits))))
if __name__=='__main__':main()
