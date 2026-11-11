import csv, hashlib, json, shutil, subprocess, tarfile
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=json.loads((BASE/'manifest.json').read_text())
    assert manifest['status']=='COMPLETED_NO_BRANCH'
    ratio=manifest['early_stop']['best_over_B1'];a=manifest['selection']['alpha'];k=manifest['selection']['k']
    # Verify actual order bytes, permutations and unchanged executed sources.
    import numpy as np
    for record in manifest['orders']:
        p=Path(record['path']);assert digest(p)==record['sha256']
        order=json.loads(p.read_text());n=len(np.load(BASE/'work/matrices'/record['matrix']/'indptr.npy',mmap_mode='r'))-1
        assert sorted(order)==list(range(n))
    for file,expected in json.loads((BASE/'logs/executed-code-hashes.json').read_text()).items():assert digest(BASE/file)==expected
    excluded=[]
    for p in (BASE/'work').iterdir():
        if p.is_file():excluded.append(dict(path=str(p),bytes=p.stat().st_size,sha256=digest(p),reason='runtime binary retained locally; excluded per T4 delivery contract'))
        elif p.name=='matrices':excluded.append(dict(path=str(p),bytes='',sha256='',reason='immutable reused T23 inputs; hashes and source paths in logs/matrices-and-taus.json and input-hash-verification.json'))
    with (BASE/'excluded-files.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,['path','bytes','sha256','reason']);w.writeheader();w.writerows(excluded)
    rows=list(csv.DictReader((BASE/'results.csv').open()))
    assert len(rows)==360 and len(manifest['orders'])==29
    assert len(rows)==len({tuple(r[x] for x in ['matrix','member_params','diag','tau','placement','d_rule','source']) for r in rows})
    assert all(r['member']=='B-RSH-ref' and r['status']=='OK' for r in rows)
    e1=manifest['E1']['comparisons'];wins=sum(x['not_worse'] for x in e1)
    text=f'''# T4 B-RSH-ref — 2026-11-11

状态：COMPLETE，按预登记早停走「否」分支。这里的 COMPLETE 表示本轮规定流程完成，不表示研究假设通过。

按选参规则后的第2轮最优/B1 = **{manifest['early_stop']['decision_metric_round2']:.9f}**，是控制器实际使用的早停值，大于0.98。以下同时给出全部已测 α/k、iso=tail 档位的原始最小值；两种读法均未达到2%，不影响早停结论。

在 cora 与 ogbn-arxiv 的 A0、W16、划分后、tail-co、own、τ=2/3 四点上，扫描最优组合相对 B1 的 T 几何均值比为 **{ratio:.9f}**（改善 **{(1-ratio)*100:.4f}%**），未达到 2%。按 <0.5% 差距偏向 B1 的规则选 α={a:g}、k={k} 供E1诊断；「否」分支的候选池 B-RSH-ref 仍按方案沿用 B1，不把这组调参成绩外推到验证集。第3轮、七张验证集、诊断扫描与 E2/E3 均 SKIPPED，未将先导或未测内容充作结果。

cora 落成自检 PASS；cora、ogbn-arxiv、reddit、ogbn-products 的 (0,8,tail) 行置换全部与冻结 B1 逐位相同，未使用空行例外。cora/arxiv 完整网格的 ΣU 与 T 也逐值相同。选中配置的 cora 独立重复置换哈希相同。原 T21/T22/T23 结果未改。

E1：near 在 {wins}/{len(e1)} 个「矩阵×τ×A0/A1」点上不差于 tail；T4-H4 = {manifest['hypotheses']['H4']}。本轮早停主结论仍是补全 α/k 未达到预登记增益门槛；E1 单列，不改变早停决定。H1b/H2/H3 未检验；H5 的贡献数值见 manifest。

运行主机：hostA-macos-arm64，MacBookPro18,3 / Apple M1 Pro / 16 GiB / 8逻辑核 / macOS15.2。纯 CPU 结构实验，无 NPU 调用或租用实例，无实例关机项。

## 参数扫描

| 参数 | A0 四点几何均值 | A1 四点几何均值 |
|---|---:|---:|
'''
    for s in manifest['parameter_scores']:text+=f"| {s['params']} | {s['A0']:.9f} | {s['A1']:.9f} |\n"
    text+='''
## 计时校准

| 校准点 | 本轮秒 | T23秒 | 比值 | 0.8–1.25 |
|---|---:|---:|---:|---|
'''
    for key,c in manifest['calibration'].items():text+=f"| {key} | {c['current_sec']:.6f} | {c['T23_sec']:.6f} | {c['ratio']:.6f} | {c['within_0_8_to_1_25']} |\n"
    text+='''
B1 校准仅合计 cora/arxiv/reddit（三张，同派发的「否」分支定义）；products 本轮也在 hostA 复现，但不进入同主机八张时间轴。C4-U 校准覆盖同主机八张。超出校准区间按方案记录，不因计时差重跑。

## 产物与状态

- `results.csv`：与 T23 同字段，仅 B-RSH-ref；A0/A1、全行与两档τ、tail/tail-co、own/D-greedy；不含 B1 行。
- `status.csv`：逐「矩阵×参数×口径」状态表，另列早停跳过项；`parameter-scores.csv` 保存全部调参及E1几何均值。
- `manifest.json`：早停数字、选参、确定性、参数生效、每次诊断、主机、校准与代码哈希。
- `pareto-audit.csv`：按原短名单规则重算的候选池前沿与类别有效性，继承成绩和时间明确标注；最终名额取舍交规划方复审。
- `orders/`：本轮全部新行序及 record；每个 record 记录文件 sha256、峰值内存和 order_sec。
- `evaluations/`：未经汇总的 T23 评价器输出、guard 与返回状态；`logs/` 保留命令、rc、stdout、stderr、构建和输入核验。
- `code/`：实际运行源码。参考实现相对原 rect.cpp 只有57行新增；在此基础上仅增加不参与排序的候选对、孤立行和分量计数。两个diff单列。
- `spec/`：本轮规格快照。评价器字节不变；按派发明确要求使用归档 v2 Layout，而非旧工作区后来演进的 v7 默认实现。

诊断中 candidates 为 top-k 截断之前、排除自身的有向去重候选行对总数；isolated 为被搜索的非空行中 kNN 边集为空的数量，空行另列。near 的局部孤立判定和移动保留派发定义，不推称论文未写明的原意。

本地 `work/` 保留新编译库及原库/输入只读链接，不进入交回包；详见 `excluded-files.csv`。SHA256SUMS 覆盖交回包内全部常规文件（自身除外）。输入与库均可由记录中的原T23本地路径恢复并核对哈希；库可用 manifest 编译命令重建。

源码、参数与硬门槛均未因结果调整。下一操作：规划方复审 manifest、结果表与原始日志，决定后续；本轮不启动新实验，不改 candidates.md。
'''
    (BASE/'README.md').write_text(text)
    (BASE/'summary.md').write_text(text)
    p=BASE/'task_plan.md';p.write_text(p.read_text().replace('- [ ]','- [x]')+'\n最终状态：T4「否」分支计算、复现、E1、八张C4校准及独立置换/哈希核验完成。\n')
    # Copy only delivery material; never follow runtime links or include binaries/caches.
    staging=Path('/private/tmp/t4-package-20261111')
    target=staging/'第一层实验结果'/BASE.name
    if target.exists():shutil.rmtree(target)
    shutil.copytree(BASE,target,ignore=shutil.ignore_patterns('work','__pycache__','SHA256SUMS'))
    entries=sorted(p for p in target.rglob('*') if p.is_file())
    sums=''.join(f'{digest(p)}  {p.relative_to(target)}\n' for p in entries)
    (target/'SHA256SUMS').write_text(sums);(BASE/'SHA256SUMS').write_text(sums)
    archive=BASE.parent/(BASE.name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:tar.add(staging/'第一层实验结果',arcname='第一层实验结果')
    # Fresh extraction verifies the delivered bytes, not just the source directory.
    verify=Path('/private/tmp/t4-package-verify-20261111');verify.mkdir(exist_ok=True)
    with tarfile.open(archive) as tar:tar.extractall(verify,filter='data')
    v=verify/'第一层实验结果'/BASE.name
    for line in (v/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1);assert digest(v/name)==expected
    receipt=dict(archive=str(archive),bytes=archive.stat().st_size,sha256=digest(archive),verified_files=len(entries),fresh_extraction_verified=True,staging=str(target),rows=len(rows))
    archive.with_suffix(archive.suffix+'.sha256').write_text(f'{receipt["sha256"]}  {archive.name}\n')
    (BASE.parent/(BASE.name+'-seal-receipt.json')).write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
