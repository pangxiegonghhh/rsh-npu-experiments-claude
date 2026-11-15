"""Add explicitly separate serial-stage-sum views to the primary M8 report."""
from pathlib import Path
import argparse,json,statistics as S,random,importlib.util

def main():
    parser=argparse.ArgumentParser();parser.add_argument('root');args=parser.parse_args();p=Path(args.root)
    spec=importlib.util.spec_from_file_location('m8analysis',p/'analyze.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    data=json.loads((p/'analysis.json').read_text(encoding='utf-8'));manifest={q['name']:q for q in json.loads((p/'manifest.json').read_text(encoding='utf-8'))};stats=data['statistics'];rng=random.Random(20261116)
    for name,q in stats.items():
        q['serial_stages']=[x+y for x,y in zip(q['reader_us_per_window'],q['pack_us_per_window'])]
    pairs=[]
    for q in data['pairs']:
        direct=stats[q['other']]['serial_stages'];pack=stats[q['pack']]['serial_stages'];difference=[y-x for x,y in zip(direct,pack)];ci=a.ci(difference,rng)
        pairs.append(dict(**{k:q[k] for k in ['tag','dtype','n','cache','direct','pack','other']},direct_stage_mean_us=S.mean(direct),pack_stage_mean_us=S.mean(pack),delta_ci95_us=ci,speedup_direct_over_pack=S.mean(direct)/S.mean(pack),winner='direct' if ci[0]>0 else 'pack' if ci[1]<0 else 'uncertain'))
    fits=[]
    for dt in [0,1]:
     for n in [16,32,64,128,256]:
      for cache in ['hot','cold']:
       for path in ['split','merge','pack']:
        cases=[mm for mm in manifest.values() if (mm['dtype'],mm['n'],mm['cache'],mm['path'])==(dt,n,cache,path) and not mm['tag'].startswith('cora')];assert len(cases)==12
        x=[[1,mm['u'],mm['r']] for mm in cases];coefficients=[];quality=[]
        for block in range(20):
            y=[stats[mm['name']]['serial_stages'][block] for mm in cases];c=a.ols(x,y);coefficients.append(c);pred=[sum(v*k for v,k in zip(row,c)) for row in x];ss=sum((v-S.mean(y))**2 for v in y)
            quality.append(dict(r2=1-sum((v-w)**2 for v,w in zip(y,pred))/ss if ss else 0,max_relative_error=max(abs(v-w)/v for v,w in zip(y,pred))))
        fits.append(dict(dtype=dt,n=n,cache=cache,path=path,mean=[S.mean(c[i] for c in coefficients) for i in range(3)],ci95=[a.ci([c[i] for c in coefficients],rng) for i in range(3)],block_coefficients=coefficients,quality=quality,qualified=all(q['r2']>=.95 and q['max_relative_error']<=.15 for q in quality)))
    bands=[]
    for primary in data['boundaries']:
        coefficients=primary['block_difference_coefficients']
        sampled=[[S.mean(coefficients[j][i] for j in indices) for i in range(3)] for indices in [rng.choices(range(20),k=20) for _ in range(2000)]]
        by_u=[]
        for u in [16,24,32,48,64,96,128,192,256]:
            roots=[-(c+a0*u)/b for c,a0,b in sampled if abs(b)>1e-15]
            by_u.append(dict(U=u,R_ci95=[a.quantile(roots,.025),a.quantile(roots,.975)] if roots else None,fraction_in_domain=sum(1<=r<=u for r in roots)/len(roots) if roots else 0))
        bands.append(dict(**{k:primary[k] for k in ['dtype','n','cache','direct','qualified','grid_result']},pointwise_boundary_root_intervals=by_u,note='Pointwise bootstrap ratio intervals. Do not clip intervals to the domain or interpret unqualified planes as a reliable boundary.'))
    output=dict(stage_pairs=pairs,stage_fits=fits,primary_boundary_bands=bands,scope='Serial stage sums average participating-core durations. Primary critical-path throughput results remain separate.')
    (p/'serial-stage-analysis.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    report=p/'M8-results-20261115.md';text=report.read_text(encoding='utf-8');marker='\n## 串行两段相加与含交接的总时间\n'
    if marker in text:text=text.split(marker)[0]
    lines=[marker,'',
      '本轮直接路的两种实现均为ND2NZ（拆分或合法合并）；尚未比较M11拟研究的普通拷贝，不能把本轮较快版本称为所有实现中的最优直接路。M1未判独立，不给重叠版本收益。','',
      '“两段相加”=(AIV打包累积时间+AIC收到READY后的读入/identity MMAD累积时间)/全卡完成窗口数，单位us/窗口，代表核心阶段平均。直接路使用相同AIC阶段时间作这一口径的对照。其配对CI和拟合另存serial-stage-analysis.json。','',
      '主报告的全卡makespan/窗口数是吞吐口径。下面将它乘24，仅换成便于和核心阶段均值比较的整卡时间等价量，仍不是单核心独立延迟；差额含交接、负载不平衡、Scalar和计时边界，不能全归因为ACK。各侧初始化在各自begin前；首窗存在跨侧启动时刻差，长批量会摊薄其影响。','',
      '|配置|AIV打包阶段均值|AIC读入/消费阶段均值|串行两段相加|24×主吞吐归一化|单位|','|---|---:|---:|---:|---:|---|']
    for name,q in stats.items():lines.append(f"|{name}|{S.mean(q['pack_us_per_window']):.8g}|{S.mean(q['reader_us_per_window']):.8g}|{S.mean(q['serial_stages']):.8g}|{24*S.mean(q['values']):.8g}|us/窗口|")
    lines+=['','## Cora：两种计时口径的对照','',
      '每个Cora配置按原170窗口序遍历不同矩阵副本，保留矩阵内行复用；最后可能多遍历不足24个窗口以凑齐整卡轮数，因此窗口数和tile数以CSV为准。B0/B1的U、R和补齐行数均变化，重排比不能只归因于段数。','',
      '|顺序|精度|N|缓存|直接路|主吞吐口径直接/pack|两段相加口径直接/pack|两段差95%CI(us/窗口)|','|---|---|---:|---|---|---:|---:|---|']
    for primary,stage in zip(data['pairs'],pairs):
        if not primary['tag'].startswith('cora'):continue
        lines.append('|'+ '|'.join(map(str,[stage['tag'],['FP16','FP32'][stage['dtype']],stage['n'],stage['cache'],stage['direct'],f"{primary['pack_speedup_direct_over_pack']:.6f}",f"{stage['speedup_direct_over_pack']:.6f}",f"[{stage['delta_ci95_us'][0]:.8g}, {stage['delta_ci95_us'][1]:.8g}]"]))+'|')
    lines+=['','原始重复值和stage总和保存在timing-observations.csv；20轮全部有效数据已本地回传并按原CSV的SHA验证。每核心stats.bin、正确性readback二进制与编译中间文件不等于已全部本地回收，完整远端归档的范围/哈希另列。','']
    report.write_text(text+'\n'.join(lines),encoding='utf-8');print(json.dumps(dict(stage_pairs=len(pairs),stage_fits=len(fits),primary_bands=len(bands))))
if __name__=='__main__':main()
