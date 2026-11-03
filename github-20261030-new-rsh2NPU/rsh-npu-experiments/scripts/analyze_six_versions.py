"""Offline, stage-separated analysis of the six completed 910B experiments.

Run with Python 3 + numpy + matplotlib. No NPU, network, or old evidence writes.
The three independent process summaries are the replication unit; 30 timed
iterations are repeated measurements, never 30 independent experimental units.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "results/analysis-20261018"
NS = (16, 64, 256)
STAGES = ("v1", "v2", "hv", "hc", "skip")
CONTRASTS = {
    "v1": [("V0", "V1", "full")],
    "v2": [("V1", "V2", "full"), ("V0", "V2", "full")],
    "hv": [("V2", "H-V", "full"), ("V0", "H-V", "full")],
    "hc": [("H-V", "H-C", "full"), ("V2", "H-C", "full"), ("V0", "H-C", "full")],
    "skip": [("V0-R", "H-Skip", "same_R_partial"), ("V2-R", "H-Skip", "same_R_partial"),
             ("H-V", "H-Skip", "unequal_output_diagnostic"), ("H-C", "H-Skip", "unequal_output_diagnostic"),
             ("V0", "H-Skip", "unequal_output_diagnostic"), ("V2", "H-Skip", "unequal_output_diagnostic"),
             ("V0", "V2", "full"), ("V0", "H-V", "full"), ("V0", "H-C", "full"),
             ("V2", "H-V", "full"), ("V2", "H-C", "full"), ("H-V", "H-C", "full")],
}
READS: dict[str, str] = {}


def read_json(path: Path):
    data = path.read_bytes()
    READS[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def gm(values):
    return float(np.exp(np.mean(np.log(values))))


def contrast_id(stage, a, b):
    return f"{stage}:{a}/{b}"


def bootstrap_matrix_interval(rows, seed=20261018):
    """Conditional matrix-composition sensitivity, NOT population inference."""
    matrices = sorted({r["matrix"] for r in rows})
    cluster_logs = np.array([np.mean([math.log(r["legacy_ratio"]) for r in rows if r["matrix"] == m]) for m in matrices])
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(matrices), (20000, len(matrices)))
    draws = np.exp(cluster_logs[indices].mean(axis=1))
    return [float(x) for x in np.quantile(draws, [.025, .975])]


def aggregate(rows):
    result = {
        "configurations": len(rows), "matrices": len({r["matrix"] for r in rows}),
        "legacy_geomean": gm([r["legacy_ratio"] for r in rows]),
        "process_logmean_geomean": float(np.exp(np.mean([r["process_logratio_mean"] for r in rows]))),
        "all_three_faster": sum(r["ratio_min"] > 1 for r in rows),
        "all_three_slower": sum(r["ratio_max"] < 1 for r in rows),
        "mixed_direction": sum(r["ratio_min"] <= 1 <= r["ratio_max"] for r in rows),
        "cluster_resampling_percentile95": bootstrap_matrix_interval(rows),
        "interval_interpretation": "Conditional sensitivity to reweighting these eight convenience-sampled matrices; not a confidence interval for unseen matrices, not within-process uncertainty.",
    }
    return result


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def load_data():
    data = {}
    latency_rows = []
    noise = {}
    provenance = {}
    for stage in STAGES:
        manifest = read_json(ROOT / f"results/{stage}/manifest.json")
        audit = read_json(ROOT / f"results/{stage}/local_audit.json")
        assert audit["passed"], stage
        provenance[stage] = {"executable_sha256": manifest["executable_sha256"], "protocol": manifest["protocol"]}
        paths = sorted((ROOT / f"results/{stage}/measurements").glob("*/N*/run*.json"))
        assert len(paths) == 72, (stage, len(paths))
        for path in paths:
            obj = read_json(path)
            assert obj["correctness"] and obj["warmups"] == 10 and obj["repeats"] == 30
            assert obj["interleaving"] == "randomized_per_call"
            assert obj["timer"] == "resident_synchronized_full_call_us"
            assert obj["b_rotation"] == 2 and obj["cores_aic"] == 24 and obj["cores_aiv"] == 48
            matrix, n, rep = path.parent.parent.name, int(path.parent.name[1:]), int(path.stem[3:])
            assert n in NS and rep in (0, 1, 2)
            record = {}
            for r in obj["records"]:
                a = np.asarray(r["samples_us"], dtype=float)
                assert a.shape == (30,) and np.all(np.isfinite(a)) and np.all(a > 0)
                assert r["variant"] not in record
                record[r["variant"]] = r
                latency_rows.append({"stage": stage, "matrix": matrix, "n": n, "process": rep,
                    "variant": r["variant"], "median_us": float(np.median(a)), "mean_us": float(a.mean()),
                    "sd_us": float(a.std(ddof=1)), "min_us": float(a.min()), "max_us": float(a.max()),
                    "p05_us": float(np.quantile(a, .05)), "p95_us": float(np.quantile(a, .95)),
                    "first_us": r["first_us"], "device_prepare_us": r["device_prepare_us"],
                    "max_abs_error": r["max_abs_error"], "valid_rows": r["valid_rows"],
                    "m": r["m"], "k16_tiles": r["k16_tiles"], "cube_groups": r["cube_groups"],
                    "aiv_rows": r["aiv_rows"], "source": str(path.relative_to(ROOT))})
            data[stage, matrix, n, rep] = record
        null_files = sorted((ROOT / f"results/{stage}/null_control").glob("*.json"))
        assert len(null_files) == 9
        all_ratio, process_ratios = [], []
        for path in null_files:
            obj = read_json(path)
            assert obj["correctness"] and len(obj["records"]) == 2
            a, b = obj["records"]
            assert a["variant"] == b["variant"]
            ratio = np.asarray(a["samples_us"]) / np.asarray(b["samples_us"])
            assert len(ratio) == 30
            all_ratio.extend(ratio.tolist())
            process_ratios.append({"source": str(path.relative_to(ROOT)), "ratio": float(np.median(ratio))})
        noise[stage] = {"null_processes": process_ratios,
            "null_iteration_p05_p95": list(map(float, np.quantile(all_ratio, [.05, .95]))),
            "null_process_median_range": [min(r["ratio"] for r in process_ratios), max(r["ratio"] for r in process_ratios)],
            "null_iteration_samples": len(all_ratio), "null_process_count": 9,
            "warning": "Descriptive only; iteration percentiles are not process-level significance thresholds."}
    return data, latency_rows, noise, provenance


def summarize(data, noise):
    all_rows, comparisons = [], {}
    matrices = sorted({k[1] for k in data})
    assert len(matrices) == 8
    for stage, contrasts in CONTRASTS.items():
        for a, b, scope in contrasts:
            rows = []
            for matrix in matrices:
                for n in NS:
                    ratios, paths, med_a, med_b = [], [], [], []
                    for rep in (0, 1, 2):
                        records = data[stage, matrix, n, rep]
                        av, bv = np.array(records[a]["samples_us"]), np.array(records[b]["samples_us"])
                        if scope in ("full", "same_R_partial"):
                            assert records[a]["valid_rows"] == records[b]["valid_rows"]
                        if scope == "full":
                            assert records[b]["valid_rows"] == records[b]["m"]
                        ratios.append(float(np.median(av/bv)))
                        med_a.append(float(np.median(av)))
                        med_b.append(float(np.median(bv)))
                        paths.append(f"results/{stage}/measurements/{matrix}/N{n}/run{rep}.json")
                    logratios = np.log(ratios)
                    row = {"comparison": contrast_id(stage, a, b), "stage": stage, "numerator": a,
                        "denominator": b, "scope": scope, "matrix": matrix, "n": n,
                        "processes": 3, "timed_iterations_per_process_per_variant": 30,
                        "ratio_run0": ratios[0], "ratio_run1": ratios[1], "ratio_run2": ratios[2],
                        "legacy_ratio": float(np.median(ratios)),
                        "process_logratio_mean": float(logratios.mean()),
                        "process_logratio_sd": float(logratios.std(ddof=1)),
                        "process_geomean_ratio": gm(ratios),
                        "ratio_min": min(ratios), "ratio_max": max(ratios),
                        "numerator_median_us": statistics.median(med_a),
                        "denominator_median_us": statistics.median(med_b),
                        "numerator_process_max_min": max(med_a)/min(med_a),
                        "denominator_process_max_min": max(med_b)/min(med_b),
                        "direction": "all_faster" if min(ratios)>1 else "all_slower" if max(ratios)<1 else "mixed",
                        "source_run0": paths[0], "source_run1": paths[1], "source_run2": paths[2]}
                    rows.append(row)
            comp = {"stage": stage, "numerator": a, "denominator": b, "scope": scope,
                "overall": aggregate(rows),
                "by_n": {str(n): aggregate([r for r in rows if r["n"] == n]) for n in NS},
                "by_matrix": {m: {"legacy_geomean": gm([r["legacy_ratio"] for r in rows if r["matrix"] == m]),
                    "process_logmean_geomean": float(np.exp(np.mean([r["process_logratio_mean"] for r in rows if r["matrix"] == m])))} for m in matrices},
                "rows": rows}
            comparisons[contrast_id(stage, a, b)] = comp
            all_rows.extend(rows)
    # Verify recomputed legacy estimators against original audit summaries.
    verify = {"v1:V0/V1": ("v1", "geomean_paired_speedup"),
              "v2:V1/V2": ("v2", "v1_over_v2_geomean"), "v2:V0/V2": ("v2", "v0_over_v2_geomean"),
              "hv:V2/H-V": ("hv", "v2_over_hv_geomean"), "hv:V0/H-V": ("hv", "v0_over_hv_geomean"),
              "hc:H-V/H-C": ("hc", "hv_over_hc_geomean")}
    verified = []
    for key, (stage, field) in verify.items():
        old = read_json(ROOT/f"results/{stage}/local_audit.json")
        assert field in old, (stage, field)
        np.testing.assert_allclose(comparisons[key]["overall"]["legacy_geomean"], old[field], rtol=1e-12)
        verified.append(key)
    old = read_json(ROOT/"results/skip/local_audit.json")
    for a, oldkey, group in [("V0-R", "v0r", "same_r"), ("V2-R", "v2r", "same_r"),
                            ("H-V", "hv", "optimistic_full"), ("H-C", "hc", "optimistic_full")]:
        key = contrast_id("skip", a, "H-Skip")
        np.testing.assert_allclose(comparisons[key]["overall"]["legacy_geomean"], old[group][oldkey+"_over_skip"]["geomean"], rtol=1e-12)
        verified.append(key)
    # A post-hoc comparator envelope, not a measured adaptive algorithm.
    oracle = {}
    for stage, b in [("hv", "H-V"), ("hc", "H-C"), ("skip", "H-V"), ("skip", "H-C")]:
        ca = comparisons[contrast_id(stage,"V0",b)]["rows"]
        cb = comparisons[contrast_id(stage,"V2",b)]["rows"]
        point = [{"matrix":ra["matrix"], "n":ra["n"], "ratio":min(ra["legacy_ratio"], rb["legacy_ratio"])} for ra,rb in zip(ca,cb)]
        oracle[f"{stage}:min(V0,{('V2')})/{b}"] = {"description":"Pointwise minimum of two comparison medians; post-hoc reference envelope, not a runnable selector or significance test.",
            "geomean":gm([r["ratio"] for r in point]), "by_n":{str(n):gm([r["ratio"] for r in point if r["n"]==n]) for n in NS},
            "rows":point}
    return comparisons, all_rows, verified, oracle


def structural_table():
    v2 = {x["matrix"]: x for x in read_json(ROOT/"results/v2/local_audit.json")["structure"]}
    hv = {x["matrix"]: x for x in read_json(ROOT/"results/hv/local_audit.json")["structure"]}
    hc = {x["matrix"]: x for x in read_json(ROOT/"results/hc/local_audit.json")["structure"]}
    diag = {x["matrix"]: x for x in read_json(ROOT/"results/v2/structure_diagnostics.json")}
    rows=[]
    for matrix in sorted(v2):
        a,b,c,d = v2[matrix],hv[matrix],hc[matrix],diag[matrix]
        rows.append({"matrix":matrix,"m":a["m"],"nnz":a["nnz"],
            "v1_k16_tiles":a["v1_k16_tiles"],"v2_k16_tiles":a["k16_tiles"],"hv_k16_tiles":b["k16_tiles"],
            "reorder_tile_reduction_percent":100*(1-a["k16_tiles"]/a["v1_k16_tiles"]),
            "hybrid_tile_reduction_percent":100*(1-b["k16_tiles"]/a["k16_tiles"]),
            "G_rows":b["G"]["rows"],"S_rows":b["S"]["rows"],"T_rows":b["T"]["rows"],"Z_rows":b["Z"]["rows"],
            "G_nnz_percent":100*b["G"]["nnz"]/a["nnz"],"S_nnz_percent":100*b["S"]["nnz"]/a["nnz"],
            "T_nnz_percent":100*b["T"]["nnz"]/a["nnz"],
            "T_row_percent":100*b["T"]["rows"]/a["m"],"tail_cube_k16_tiles":c["tail_k16_tiles"],
            "v1_core_tile_max_mean":d["v1_max_mean"],"v2_core_tile_max_mean":d["v2_max_mean"],
            "reorder_seconds":a["seconds"],"hv_partition_seconds":b["partition_seconds"],"hv_layout_seconds":b["layout_seconds"],
            "sources": [f"results/v2/orders/{matrix}/structure.json",f"results/hv/plans/{matrix}/structure.json",f"results/hc/plans/{matrix}/structure.json","results/v2/structure_diagnostics.json"]})
    for row in rows:
        for source in row["sources"]:
            assert (ROOT/source).exists(),source
            read_json(ROOT/source)
    return rows


def setup_plot():
    os.environ.setdefault("MPLCONFIGDIR", str(DEST/".mpl-cache"))
    # Reuse existing local dependency cache only; never install/download packages.
    for package in ["matplotlib","PIL","contourpy","cycler","fontTools","kiwisolver","pyparsing","dateutil","packaging"]:
        if importlib.util.find_spec(package) is None:
            matches=list((Path.home()/".cache/uv/archive-v0").glob(f"*/{package}/__init__.py"))
            if matches:
                sys.path.append(str(sorted(matches)[0].parents[1]))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10, "axes.spines.top":False,
                         "axes.spines.right":False,"pdf.fonttype":42,"savefig.dpi":180})
    return plt,TwoSlopeNorm,matplotlib.__version__


def figures(stats):
    plt, normclass, version = setup_plot()
    out=DEST/"figures";out.mkdir(exist_ok=True)
    comps=stats["comparisons"]
    matrices=sorted({r["matrix"] for r in stats["structure"]})
    labels=[m.replace("SNAP_", "").replace("Boeing_", "").replace("FEMLAB_", "").replace("HB_", "").replace("Schmid_", "") for m in matrices]
    def save(fig,name):
        fig.savefig(out/(name+".png"),bbox_inches="tight",facecolor="white")
        fig.savefig(out/(name+".pdf"),bbox_inches="tight",facecolor="white")
        plt.close(fig)
    # Exact values are annotated; color uses log2 ratio and symmetric bounds.
    keys=["v2:V1/V2","hv:V2/H-V","hc:H-V/H-C","skip:V2-R/H-Skip"]
    titles=["Reordering\nV1 / V2 (V2 stage)","Routing\nV2 / H-V (H-V stage)","Tail placement\nH-V / H-C (H-C stage)","Same retained rows R\nV2-R / H-Skip (Skip stage)"]
    fig,axes=plt.subplots(1,4,figsize=(13.8,6.1),sharey=True)
    for ax,key,title in zip(axes,keys,titles):
        lookup={(r["matrix"],r["n"]):r for r in comps[key]["rows"]}
        vals=np.array([[lookup[m,n]["legacy_ratio"] for n in NS] for m in matrices])
        im=ax.imshow(np.log2(vals),cmap="RdBu",norm=normclass(vmin=-.7,vcenter=0,vmax=.7),aspect="auto")
        for i,m in enumerate(matrices):
            for j,n in enumerate(NS):
                marker="" if lookup[m,n]["direction"]!="mixed" else "*"
                ax.text(j,i,f"{vals[i,j]:.2f}{marker}",ha="center",va="center",fontsize=9,
                        color="white" if abs(np.log2(vals[i,j]))>.42 else "black")
        ax.set_xticks(range(3),[str(n) for n in NS]);ax.set_xlabel("Dense width N")
        ax.set_title(title,fontsize=10,pad=12)
    axes[0].set_yticks(range(8),labels)
    fig.suptitle("Incremental benefits are workload dependent",fontsize=15,y=.99)
    fig.subplots_adjust(left=.13,right=.91,bottom=.15,top=.84,wspace=.12)
    cax=fig.add_axes([.93,.21,.012,.56]);cb=fig.colorbar(im,cax=cax,extend="both")
    cb.set_ticks([math.log2(.75),0,math.log2(1.5)]);cb.set_ticklabels(["0.75×","1×","1.5×"])
    fig.text(.13,.035,"Ratios > 1 favor the denominator. * Three process ratios have mixed directions.\nValues are median-of-three paired process ratios; stages are kept separate. H-Skip computes only R.",fontsize=9)
    save(fig,"figure-01-incremental-heatmaps")

    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for key,label,color in [("skip:V0/V2","V2","#0072B2"),("skip:V0/H-V","H-V","#D55E00"),("skip:V0/H-C","H-C","#009E73")]:
        cs=comps[key]
        ys=[cs["by_n"][str(n)]["legacy_geomean"] for n in NS]
        axes[0].plot(range(3),ys,"o-",color=color,label=label)
        for j,n in enumerate(NS):
            lo,hi=cs["by_n"][str(n)]["cluster_resampling_percentile95"]
            axes[0].plot([j,j],[lo,hi],color=color,alpha=.35,linewidth=2)
    axes[0].set_xticks(range(3),[str(n) for n in NS]);axes[0].set_xlabel("Dense width N")
    axes[0].set_ylabel("V0 / full-output method")
    axes[0].set_title("Same-process full-output controls, Skip stage")
    axes[0].axhline(1,color="gray",ls="--",lw=1);axes[0].legend(frameon=False)
    n16=comps["skip:V0/H-V"]["rows"]
    vals=np.array([[next(r["legacy_ratio"] for r in n16 if r["matrix"]==m and r["n"]==n) for n in NS]for m in matrices])
    xx=np.arange(8)
    for j,(n,color) in enumerate(zip(NS,["#0072B2","#E69F00","#009E73"])):
        axes[1].plot(xx,vals[:,j],"o-",label=f"N={n}",color=color)
    axes[1].set_xticks(xx,labels,rotation=45,ha="right");axes[1].set_yscale("log")
    axes[1].set_ylabel("V0 / H-V (log scale)");axes[1].axhline(1,color="gray",ls="--",lw=1)
    axes[1].set_title("Aggregate gains hide matrix dependence");axes[1].legend(frameon=False,fontsize=8)
    fig.tight_layout(rect=[0,.10,1,1])
    fig.text(.04,.015,"Lines: geometric mean of point ratios (left), individual point ratios (right). Left bars: 95% matrix-resampling\npercentile range; conditional composition sensitivity, not population inference or process-level confidence intervals.",fontsize=8.5)
    save(fig,"figure-02-full-output-width-effect")

    fig,axes=plt.subplots(1,3,figsize=(14.2,5.0))
    st=stats["structure"];y=np.arange(8)
    axes[0].barh(y-.16,[r["reorder_tile_reduction_percent"] for r in st],height=.29,label="V1 → V2",color="#0072B2")
    axes[0].barh(y+.16,[r["hybrid_tile_reduction_percent"] for r in st],height=.29,label="V2 → H-V",color="#D55E00")
    axes[0].set_yticks(y,labels);axes[0].invert_yaxis();axes[0].set_xlabel("Reduction in k16 tiles (%)")
    axes[0].set_title("Structural work reduction");axes[0].legend(frameon=False)
    axes[1].barh(y,[r["S_nnz_percent"] for r in st],color="#009E73",label="S (AIV)")
    axes[1].barh(y,[r["T_nnz_percent"] for r in st],left=[r["S_nnz_percent"] for r in st],color="#E69F00",label="T (tail)")
    axes[1].set_yticks(y,labels);axes[1].invert_yaxis();axes[1].set_xlabel("Fraction of original nonzeros (%)")
    axes[1].set_title("AIV / tail work is often small");axes[1].legend(frameon=False)
    ratios=[max(r["denominator_process_max_min"] for r in comps["skip:V2-R/H-Skip"]["rows"] if r["matrix"]==m) for m in matrices]
    axes[2].barh(y,ratios,color="#CC79A7");axes[2].set_yticks(y,labels);axes[2].invert_yaxis()
    axes[2].axvline(1,color="gray",ls="--",lw=1);axes[2].set_xlabel("max / min process-median latency")
    axes[2].set_title("H-Skip noise, worst width per matrix")
    fig.tight_layout(rect=[0,.10,1,1])
    fig.text(.025,.015,"Frozen routing at thresholds (4, 2), W=16. Tile counts are work proxies, not measured kernel time.\nNoise panel retains all three processes and all widths; max/min is descriptive and does not identify a cause.",fontsize=9)
    save(fig,"figure-03-structure-tail-noise")

    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for i,stage in enumerate(STAGES):
        q=stats["noise"][stage]
        ratios=[r["ratio"] for r in q["null_processes"]]
        axes[0].scatter(np.full(9,i)+np.linspace(-.13,.13,9),ratios,s=25,label=stage)
        lo,hi=q["null_iteration_p05_p95"]
        axes[0].plot([i,i],[lo,hi],color="gray",alpha=.45,lw=5)
    axes[0].set_xticks(range(5),["V1","V2","H-V","H-C","H-Skip"])
    axes[0].axhline(1,color="black",ls="--",lw=1);axes[0].set_ylabel("Identical implementation / itself")
    axes[0].set_title("Null controls: process vs iteration scales")
    for stage,col,label in [("v2","#0072B2","V1/V2, V2 stage"),("hv","#D55E00","V2/H-V, H-V stage"),("skip","#009E73","V2-R/H-Skip, Skip stage")]:
        key={"v2":"v2:V1/V2","hv":"hv:V2/H-V","skip":"skip:V2-R/H-Skip"}[stage]
        rr=comps[key]["rows"]
        spread=sorted([r["ratio_max"]/r["ratio_min"] for r in rr])
        axes[1].plot(range(1,25),spread,"o-",label=label,color=col,ms=3)
    axes[1].axhline(1,color="gray",ls="--",lw=1);axes[1].set_xlabel("Configurations sorted within contrast")
    axes[1].set_ylabel("max / min of three paired process ratios")
    axes[1].set_title("Pairing helps, but does not erase variability");axes[1].legend(frameon=False,fontsize=8)
    fig.tight_layout(rect=[0,.10,1,1])
    fig.text(.035,.02,"Left dots: nine process medians; gray lines: 5th–95th percentiles of 270 iteration ratios. Different units must not\nbe used interchangeably as acceptance thresholds. Right curves keep every point; no outlier removal.",fontsize=8.5)
    save(fig,"figure-04-noise-scales")
    return version


def write_markdown(stats):
    comparisons=stats["comparisons"]
    summary=["# 六版本：阶段内原始配对统计", "", "分子/分母>1表示分母更快。各阶段独立分析，不用跨阶段绝对时间算加速。精确数值见CSV/JSON；下表显示6位小数。", "",
             "| 测量阶段 | 比较 | 输出范围 | 24点几何平均 | 3进程log均值口径 | 三进程均快/均慢/混合 | N16 | N64 | N256 |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for key,c in comparisons.items():
        a=c["overall"]
        summary.append(f"| {c['stage']} | {c['numerator']}/{c['denominator']} | {c['scope']} | {a['legacy_geomean']:.6f} | {a['process_logmean_geomean']:.6f} | {a['all_three_faster']}/{a['all_three_slower']}/{a['mixed_direction']} | "+" | ".join(f"{c['by_n'][str(n)]['legacy_geomean']:.6f}" for n in NS)+" |")
    summary += ["", "full为相同完整输出；same_R_partial仅相同保留集合R；unequal_output_diagnostic分子完整、分母只算R，不能称完整SpMM加速，也不是严格数学上界。", "", "## 每点原始三进程范围", "", "下表process log mean±SD为三个进程配对中位比的自然对数统计；range为三进程原始比最小–最大。没有把30轮当作30个独立样本。"]
    for key,c in comparisons.items():
        summary += ["", f"### {key}", "", "| 矩阵 | N | run0 | run1 | run2 | 中位比 | log mean ± SD | 最小–最大 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for r in c["rows"]:
            summary.append(f"| {r['matrix']} | {r['n']} | {r['ratio_run0']:.6f} | {r['ratio_run1']:.6f} | {r['ratio_run2']:.6f} | {r['legacy_ratio']:.6f} | {r['process_logratio_mean']:.6f} ± {r['process_logratio_sd']:.6f} | {r['ratio_min']:.6f}–{r['ratio_max']:.6f} |")
    (DEST/"tables.md").write_text("\n".join(summary)+"\n")
    appendix=["# 统计附录：六主版本离线复核", "", "## 分析问题与边界", "",
        "逐阶段比较可归因的增量：V1评估固定窗Cube，V2评估重排，H-V评估分流与动态成组，H-C评估冻结尾部改走Cube，H-Skip评估排除T后的相同R主体。另使用H-Skip阶段的同进程完整V0/V2/H-V/H-C，避免跨轮绝对时间漂移。没有新NPU测量、没有删除任何原始点。", "",
        "## 原始样本、单位与估计量", "",
        "每阶段8矩阵×3个N（16/64/256）×3独立进程；每进程每版本10预热+30计时轮，逐轮随机交错、两份B轮换。计时为resident_synchronized_full_call_us，包含完整驻留调用和同步，排除CPU预处理与首次H2D。V1/V2/H-V/H-C/H-Skip分别2/3/3/4/7个同进程版本。V0初始单路径计时只作历史运行证据，未与后阶段作跨轮速度比。", "",
        "以每个原始JSON为来源。先每轮计算 a_i/b_i，再对30轮取中位得到进程比r_j；每点以median(r_0,r_1,r_2)保留历史口径，24点以exp(mean(log(point ratio)))汇总。另提供mean(log r_j)、样本SD(ddof=1)、exp(mean(log r_j))及[min,max]，显示3次重复的不稳定性。这两个汇总口径不相等时不暗中替换。", "",
        "每个矩阵的3个N重复测同一结构，24点不是24个独立矩阵；同一进程的30轮也不是30个独立实验。对同进程版本可配对，对不同阶段绝对耗时不可直接配对。每点只有3进程，且租用设备状态有漂移，正态性/独立同分布假设无法可靠检验，因此不计算或宣称逐点显著性、稳健95%置信区间、伪p值。", "",
        "## 区间、效应量与多重比较", "",
        "效应量为配对时间比；>1表示分母更快。无假设检验，故不报告p值、显著/不显著或多重比较校正后的发现。若将这些探索性多对比带入后续验证，须预先冻结主要对比和门槛，并用新进程/新矩阵验证。", "",
        "JSON/CSV另给20,000次矩阵cluster重抽样的2.5%–97.5%范围：固定seed=20261018，每次对8矩阵有放回抽8个，保留其3个N和既有点估计。此范围只显示这8个便利抽样矩阵被重新加权时的组成敏感性，不是面向未知矩阵总体的95%CI；没有纳入3进程测量误差。它不可替代更多独立测量。", "",
        "## 阶段内汇总与矩阵重加权范围", "", "| 阶段/比较 | 几何平均 | 条件矩阵重加权95%范围 |", "|---|---:|---:|"]
    for key,c in comparisons.items():
        a=c["overall"];lo,hi=a["cluster_resampling_percentile95"]
        appendix.append(f"| {key} | {a['legacy_geomean']:.6f} | {lo:.6f}–{hi:.6f} |")
    appendix += ["", "## 噪声尺度", "", "每阶段有9个同实现/同实现空对照进程。270个逐轮比的p05/p95与9个进程中位比的min/max描述的是不同尺度；历史H-V用逐轮p95作为聚合阈值保护线较保守，本附录保留旧判定，不追溯改判。后续协议应使用与主要效应相同的进程级或时段级单位。", "", "| 阶段 | 逐轮p05–p95 | 进程中位比min–max |", "|---|---:|---:|"]
    for stage,no in stats["noise"].items():
        a,b=no["null_iteration_p05_p95"];c,d=no["null_process_median_range"]
        appendix.append(f"| {stage} | {a:.6f}–{b:.6f} | {c:.6f}–{d:.6f} |")
    appendix += ["", "所有慢点保留。max/min幅度不等同于变异系数，不证明热降频、竞争、缓存或驱动中的任何具体原因。原始计时和运行顺序缺少足够设备遥测，现阶段只能标记噪声及规划可证伪诊断。", "",
        "## 科学解释限制", "", "- 固定后端上的受控消融，不是对Neutron或厂商最强库的排名。", "- H-Skip仅计算R；完整H-V/H-C除以H-Skip是不同输出工作量的诊断，不能作为完整输出加速，也不能通过相减估计纯尾部成本。", "- 所有R版本仍清零完整M输出。Cube恢复按已布局group槽和rowmap进行；没有紧凑|R|输出实现。", "- 分组k16块数、S/T非零量及静态每核块数仅是结构工作量代理，不等于真实时延或内存峰值。", "- 只在这8矩阵、3宽度、固定4/2策略和现有实现上成立；N16→N256并未独立改变结构。", "- CPU预处理、H2D与复用摊销没有计入主要速度比；不能据此宣称完整端到端加速。", "- 三进程均快是方向一致性描述，不是显著性结论。", "",
        "## 可复现与证据", "", "运行scripts/analyze_six_versions.py仅读取历史数据并写results/analysis-20261018。stats.json的source_sha256列出每个读取文件及SHA256，source协议和可执行文件摘要按阶段保存。point-comparisons.csv含每点run0/run1/run2来源；process-latencies.csv保留每版本逐进程时延描述；本分析没有覆盖或重写历史audit。", "",
        f"复算通过的历史汇总检查：{', '.join(stats['verified_legacy_comparisons'])}。所有{len(stats['point_rows'])}条比较点都从实际原始样本计算；CSV全精度保留浮点值。", ""]
    (DEST/"stats-appendix.md").write_text("\n".join(appendix))
    catalog="""# 图目录与解释约束

全部图是实际本地数据生成的PNG/PDF；图中英文用于避免字体依赖。主表见tables.md，精确数据见point-comparisons.csv与structure.csv。图1–4都不是统计显著性图。

## figure-01-incremental-heatmaps

- 文件：figures/figure-01-incremental-heatmaps.png、.pdf。
- 目的：区分重排、分流、尾部路径及部分主体的增量，不把六版混成单一总体速度。
- 来源：V2/H-V/H-C/Skip各自measurements原始JSON；实际数值在stats.json对应comparison.rows。
- 变量：8矩阵×3N的进程配对中位比；颜色为log2比，中心1；色阶截断范围外仍显示准确数字。
- 图注必须说明：>1分母快，星号表示3进程方向混合；每点3进程，每进程30轮，后者非独立样本。H-Skip列只计算R，前三列完整输出；阶段不能交叉用绝对耗时相除。
- 观察：重排在ns3Da等点收益强，分流收益集中而尾部换路接近1；部分R收益不自动代表完整输出收益。
- 决策含义：优先验证分流增量的适用结构和计时稳定性，不能仅凭V0相对收益确定框架创新。
- 检查：颜色和数字方向一致；星号按三进程比生成；不称星号外点“显著”。

## figure-02-full-output-width-effect

- 文件：figures/figure-02-full-output-width-effect.png、.pdf。
- 目的：用H-Skip阶段同进程完整V0/V2/H-V/H-C控制，展示N和矩阵依赖。
- 来源：results/skip/measurements/*/N*/run*.json；比较skip:V0/V2、skip:V0/H-V、skip:V0/H-C。
- 变量：左图每宽度8矩阵几何平均；误差线是对8矩阵进行20,000次重加权的2.5%–97.5%条件范围。右图每矩阵完整V0/H-V的3宽度点，y轴对数。
- 图注必须说明：固定便利矩阵集的组成敏感性，不是未知总体CI，不是3进程CI；仍非端到端。
- 观察：N增大后当前Cube/混合相对V0的平均优势下降，收益强烈依赖矩阵。
- 决策含义：不能只报全部24点的一个geomean；下一轮应按结构×N设计诊断和路径选择。
- 检查：左边条不解释为显著性；右边非独立样本点不做回归因果推断。

## figure-03-structure-tail-noise

- 文件：figures/figure-03-structure-tail-noise.png、.pdf。
- 目的：把结构工作量减少、尾窗比例和进程波动三类证据并排展示。
- 来源：results/v2/orders/*/structure.json、results/hv/plans/*/structure.json、results/hc/plans/*/structure.json；Skip原始计时。structure.csv精确记录字段和来源。
- 变量：k16块减少比例；S/T原始非零比例；H-Skip同配置3进程median的max/min，并取同矩阵3宽度最大值。
- 图注必须说明：固定4/2、W16；块数是代理；噪声极差不是方差且选取最差宽度。没有误差线。
- 观察：尾部原始非零比例很小；分流删除的Cube块量随矩阵差异大；部分矩阵的噪声比预计增量大。
- 决策含义：尾窗优化优先级应降低，先检查结构减少为何没有稳定变成时延减少；先诊断波动再判断百分之几收益。
- 检查：不把T占比直接转换为精确理论加速上界；不把过程波动归因于某具体硬件机制。

## figure-04-noise-scales

- 文件：figures/figure-04-noise-scales.png、.pdf。
- 目的：解释为何逐轮噪声包络和进程级收益门槛不能混用，以及配对剩余波动。
- 来源：五阶段null_control/*.json；V2/H-V/Skip的原始正式measurements。
- 变量：左边每阶段9个空对照进程中位比（点），270逐轮比p05–p95（灰线）；右边各比较24点的3进程比max/min排序。
- 图注必须说明：灰线为描述分位范围而非95%置信区间；不同曲线内分别排序，横坐标不能作同一配置配对。
- 观察：逐轮包络宽得多，部分正式配对比仍有明显波动。
- 决策含义：下一次门槛与采样单位对齐；不得因为未超过历史逐轮p95就称候选无收益。
- 检查：右曲线排序独立；没有删除离群点；不把灰线内外当作统计显著性。
"""
    (DEST/"figure-catalog.md").write_text(catalog)


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    data, latency, noise, provenance=load_data()
    comparisons, rows, verified, oracle=summarize(data,noise)
    structures=structural_table()
    stats={"schema":"six-version-offline-analysis-v1","analysis_date":"2026-10-18",
        "replication_unit":"independent process; 3 per configuration", "iteration_count":30,
        "matrix_count":8,"widths":list(NS),"stages":list(STAGES),
        "comparison_count":len(comparisons),"comparisons":comparisons,"point_rows":rows,
        "noise":noise,"structure":structures,"posthoc_reference_envelope":oracle,
        "verified_legacy_comparisons":verified,"source_protocols":provenance,
        "inference":"descriptive; no p values, no per-point 95% CI; conditional matrix-resampling sensitivity only"}
    summaries=[]
    for key,c in comparisons.items():
        summaries.append({"comparison":key,"scope":c["scope"],**c["overall"],
            **{f"N{n}_geomean":c["by_n"][str(n)]["legacy_geomean"] for n in NS}})
    write_csv(DEST/"comparison-summary.csv",summaries)
    write_csv(DEST/"point-comparisons.csv",rows)
    write_csv(DEST/"process-latencies.csv",latency)
    write_csv(DEST/"structure.csv",structures)
    write_csv(DEST/"by-matrix.csv",[{"comparison":key,"matrix":m,**x} for key,c in comparisons.items() for m,x in c["by_matrix"].items()])
    stats["matplotlib_version"]=figures(stats)
    stats["numpy_version"]=np.__version__
    stats["source_sha256"]=READS
    stats["analysis_script_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    write_markdown(stats)
    (DEST/"stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"comparisons":len(comparisons),"point_rows":len(rows),"process_variant_rows":len(latency),"sources":len(READS),"figures":4,"output":str(DEST)},ensure_ascii=False))
    for key,c in comparisons.items():
        print(key,json.dumps(c["overall"],ensure_ascii=False))


if __name__ == "__main__":
    main()
