#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T8 CPU 侧数据准备（计划 §6 的 8 项输出）。

只用标准库。运行方式： python3 -I -B t8_cpu_prep.py --help

输入
  --matrix     稀疏矩阵 A。Matrix Market 坐标格式（.mtx），或每行 "行 列 [值]" 的文本边表。
  --row-order  行序文件：每行一个整数，第 i 行（从 0 数）= 放到新位置 i 的原始行号。不给则为原始序。
  --col-order  列序文件，格式同上；写 same 表示列与行用同一置换。不给则列不动。
  --aiv-rows   可选。交给 AIV 的行（新行序下的行号，每行一个）。给了才产出第 5 项。

定义（与计划 §1.4 一致）
  窗口 w   新行序下第 w*W .. w*W+W-1 行。
  U_w      窗口内所有非零的列号去重后的个数（要取的稠密 B 的行数）。
  R_w      这 U_w 个列号排序后，连续整数合并成的段数。
  段间距   相邻两段之间空着的行数（后段起点 - 前段终点 - 1）。

退出码  0 正常；2 自检（--expect-*）不符，此时不写 replay/；1 输入有误。
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sys

VERSION = "t8_cpu_prep 1.0 (2026-11-14)"

# M5 的测试范围（计划 M5 第 2 步），用于第 3 项分档
M5_LENS = (1, 2, 4)
M5_GAPS = (2, 8, 64)
M5_MAX_COUNT = 16


def die(msg):
    sys.stderr.write("错误: %s\n" % msg)
    sys.exit(1)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def read_matrix(path, index_base, symmetrize, nrows_arg, ncols_arg):
    """返回 (nrows, ncols, set((r, c)))，下标从 0 起。"""
    ent = set()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        first = f.readline()
        if first.startswith("%%MatrixMarket"):
            hdr = first.lower().split()
            if len(hdr) < 5 or hdr[2] != "coordinate":
                die("只支持 Matrix Market 坐标格式")
            sym = hdr[4] in ("symmetric", "skew-symmetric", "hermitian")
            line = f.readline()
            while line.startswith("%"):
                line = f.readline()
            nr, nc, _ = (int(x) for x in line.split()[:3])
            for line in f:
                p = line.split()
                if not p:
                    continue
                r, c = int(p[0]) - 1, int(p[1]) - 1
                ent.add((r, c))
                if sym or symmetrize:
                    ent.add((c, r))
            return nr, nc, ent
        lines = [first] + f.readlines()
    mr = mc = -1
    for line in lines:
        s = line.strip()
        if not s or s[0] in "#%":
            continue
        p = s.replace(",", " ").split()
        r, c = int(p[0]) - index_base, int(p[1]) - index_base
        if r < 0 or c < 0:
            die("出现负下标，检查 --index-base")
        ent.add((r, c))
        if symmetrize:
            ent.add((c, r))
        mr, mc = max(mr, r, c if symmetrize else r), max(mc, c, r if symmetrize else c)
    nr = nrows_arg if nrows_arg else mr + 1
    nc = ncols_arg if ncols_arg else mc + 1
    if symmetrize:
        nr = nc = max(nr, nc)
    return nr, nc, ent


def read_perm(path, n, base):
    with open(path, "r", encoding="utf-8") as f:
        v = [int(s.split()[0]) - base for s in f if s.strip() and s.strip()[0] not in "#%"]
    if len(v) != n or sorted(v) != list(range(n)):
        die("%s 不是 0..%d 的一个置换（长度 %d）" % (path, n - 1, len(v)))
    return v


def runs(sorted_ints):
    """升序且无重复的整数表 -> [(起点, 长度), ...]"""
    out = []
    for x in sorted_ints:
        if out and x == out[-1][0] + out[-1][1]:
            out[-1][1] += 1
        else:
            out.append([x, 1])
    return [(s, l) for s, l in out]


def gaps_of(segs):
    return [segs[i + 1][0] - segs[i][0] - segs[i][1] for i in range(len(segs) - 1)]


def equi_groups(segs):
    """贪心地把段表切成极大的「等长且等间距」组。返回 [(组内段数, 段长, 间距), ...]；单段组间距记 -1。"""
    out, i, n = [], 0, len(segs)
    while i < n:
        j = i
        if i + 1 < n and segs[i + 1][1] == segs[i][1]:
            stride = segs[i + 1][0] - segs[i][0]
            j = i + 1
            while j + 1 < n and segs[j + 1][1] == segs[i][1] and segs[j + 1][0] - segs[j][0] == stride:
                j += 1
            out.append((j - i + 1, segs[i][1], stride - segs[i][1]))
        else:
            out.append((1, segs[i][1], -1))
        i = j + 1
    return out


def m5_bucket(count, seglen, gap):
    if count < 2:
        return "single"
    if seglen in M5_LENS and gap in M5_GAPS:
        return "m5_exact"          # 段长、间距都正好是 M5 测过的取值
    if seglen <= max(M5_LENS) and gap <= max(M5_GAPS):
        return "m5_envelope"       # 落在 M5 取值的包络内，但不是测过的点
    return "outside"


def quantile_nr(sorted_v, p):
    """最近秩法分位数。"""
    if not sorted_v:
        return None
    return sorted_v[max(0, math.ceil(p * len(sorted_v)) - 1)]


def median_interp(sorted_v):
    n = len(sorted_v)
    if n == 0:
        return None
    return sorted_v[n // 2] if n % 2 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2.0


def dist(values):
    v = sorted(values)
    if not v:
        return {"n": 0}
    return {"n": len(v), "sum": sum(v), "min": v[0], "p25": quantile_nr(v, .25),
            "p50": quantile_nr(v, .5), "p50_interp": median_interp(v),
            "p75": quantile_nr(v, .75), "p90": quantile_nr(v, .9),
            "p99": quantile_nr(v, .99), "max": v[-1], "mean": sum(v) / len(v)}


def hist(values):
    h = {}
    for x in values:
        h[x] = h.get(x, 0) + 1
    return sorted(h.items())


def wcsv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def jl(xs):
    return ";".join(str(x) for x in xs)


def main():
    ap = argparse.ArgumentParser(description="T8 CPU 侧数据准备（§6）")
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--tag", required=True, help="本次输出的标签，如 cora-A0-W16-B0")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--row-order")
    ap.add_argument("--col-order", help="列序文件，或 same")
    ap.add_argument("--aiv-rows")
    ap.add_argument("--W", type=int, default=16)
    ap.add_argument("--k", type=int, default=16, help="K 方向切块行数（第 4 项）")
    ap.add_argument("--ring", type=int, default=64, help="第 7 项「近 L 次内重复」的 L")
    ap.add_argument("--drop-diag", choices=("yes", "no"), required=True, help="是否去掉对角元")
    ap.add_argument("--tail", choices=("keep", "drop"), required=True, help="不满 W 行的尾窗：保留 / 丢弃")
    ap.add_argument("--index-base", type=int, default=0, help="文本边表的下标起点")
    ap.add_argument("--order-base", type=int, default=0, help="行序/列序/AIV 行文件的下标起点")
    ap.add_argument("--symmetrize", action="store_true", help="文本边表按无向图补对称元")
    ap.add_argument("--nrows", type=int)
    ap.add_argument("--ncols", type=int)
    ap.add_argument("--expect-sumU", type=int)
    ap.add_argument("--expect-sumR", type=int)
    ap.add_argument("--expect-R-p50", type=float)
    ap.add_argument("--expect-R-max", type=int)
    a = ap.parse_args()

    nr, nc, ent = read_matrix(a.matrix, a.index_base, a.symmetrize, a.nrows, a.ncols)
    nnz_in = len(ent)
    if a.drop_diag == "yes":
        ent = {(r, c) for r, c in ent if r != c}
    perm = read_perm(a.row_order, nr, a.order_base) if a.row_order else list(range(nr))
    if a.col_order == "same":
        if nr != nc:
            die("--col-order same 要求方阵")
        cperm = perm
    elif a.col_order:
        cperm = read_perm(a.col_order, nc, a.order_base)
    else:
        cperm = None
    cpos = None
    if cperm is not None:
        cpos = [0] * nc
        for i, o in enumerate(cperm):
            cpos[o] = i
    by_row = [[] for _ in range(nr)]
    for r, c in ent:
        by_row[r].append(cpos[c] if cpos else c)
    rows = [sorted(by_row[perm[i]]) for i in range(nr)]   # 新行序

    nwin = nr // a.W if a.tail == "drop" else (nr + a.W - 1) // a.W
    nrow_used = min(nr, nwin * a.W)

    aiv = None
    if a.aiv_rows:
        with open(a.aiv_rows, "r", encoding="utf-8") as f:
            aiv = sorted({int(s.split()[0]) - a.order_base for s in f if s.strip() and s.strip()[0] not in "#%"})
        if aiv and (aiv[0] < 0 or aiv[-1] >= nr):
            die("--aiv-rows 行号越界")
        aiv_set = set(aiv)

    os.makedirs(a.out, exist_ok=True)
    P = lambda name: os.path.join(a.out, name)

    win_rows, chunk_rows, grp_cnt, seg_table = [], [], {}, []
    Us, Rs, instr, all_len, all_gap, wb_all = [], [], [], [], [], []
    aiv_rows_out, aivZ, aivH, aivR, aiv_len, wb_aiv, wb_aic = [], [], [], [], [], [], []
    for w in range(nwin):
        r0, r1 = w * a.W, min(nr, (w + 1) * a.W)
        cols = sorted({c for i in range(r0, r1) for c in rows[i]})
        segs = runs(cols)
        gp = gaps_of(segs)
        nnz_w = sum(len(rows[i]) for i in range(r0, r1))
        # 第 4 项：按 k 行切块后每块的段数
        per_chunk = []
        for j in range(0, len(cols), a.k):
            cs = runs(cols[j:j + a.k])
            per_chunk.append(len(cs))
            chunk_rows.append((w, j // a.k, len(cols[j:j + a.k]), len(cs), jl(l for _, l in cs)))
        # 第 3 项
        for cnt, ln, gap in equi_groups(segs):
            key = (cnt, ln, gap)
            grp_cnt[key] = grp_cnt.get(key, 0) + 1
        Us.append(len(cols)); Rs.append(len(segs)); instr.append(sum(per_chunk))
        all_len += [l for _, l in segs]; all_gap += gp
        nonempty = [i for i in range(r0, r1) if rows[i]]
        wb_all.append(len(runs(nonempty)))
        win_rows.append((w, r0, r1 - 1, nnz_w, len(cols), len(segs), len(per_chunk), sum(per_chunk),
                         jl(l for _, l in segs), jl(gp)))
        seg_table += [(w, s, l) for s, l in segs]
        if aiv is not None:
            av = [i for i in nonempty if i in aiv_set]
            ac = [i for i in nonempty if i not in aiv_set]
            sv = runs(av)
            z = sum(len(rows[i]) for i in av)
            aivZ.append(z); aivH.append(len(av)); aivR.append(len(sv)); aiv_len += [l for _, l in sv]
            wb_aiv.append(len(sv)); wb_aic.append(len(runs(ac)))
            aiv_rows_out.append((w, z, len(av), len(sv), jl(l for _, l in sv)))

    # 第 7 项：AIV 取数序列（没给 --aiv-rows 时用全部行）
    seq_rows = [i for i in (aiv if aiv is not None else range(nrow_used)) if i < nrow_used]
    seq, last, recent_dup, win_seen, win_dup, cur_w = [], {}, 0, set(), 0, -1
    for i in seq_rows:
        if i // a.W != cur_w:
            cur_w, win_seen = i // a.W, set()
        for c in rows[i]:
            n = len(seq)
            if c in last and n - last[c] <= a.ring:
                recent_dup += 1
            if c in win_seen:
                win_dup += 1
            win_seen.add(c); last[c] = n
            seq.append((i, c))
    tot = len(seq)
    dedup = {
        "scope_rows": "aiv" if aiv is not None else "all",
        "fetches": tot,
        "distinct_cols": len(last),
        "dup_ratio_global": (1 - len(last) / tot) if tot else None,
        "dup_ratio_within_window": (win_dup / tot) if tot else None,
        "ring_L": a.ring,
        "dup_ratio_within_last_L": (recent_dup / tot) if tot else None,
    }

    # 第 3 项汇总
    nseg = sum(Rs)
    bucket_seg = {"single": 0, "m5_exact": 0, "m5_envelope": 0, "outside": 0}
    grp_rows = []
    for (cnt, ln, gap), ng in sorted(grp_cnt.items()):
        b = m5_bucket(cnt, ln, gap)
        bucket_seg[b] += cnt * ng
        grp_rows.append((cnt, ln, gap, ng, cnt * ng, b, "yes" if cnt > M5_MAX_COUNT else "no"))

    checks = {}
    def chk(name, got, exp):
        if exp is not None:
            checks[name] = {"expected": exp, "got": got, "ok": got == exp}
    sR = sorted(Rs)
    chk("sumU", sum(Us), a.expect_sumU)
    chk("sumR", sum(Rs), a.expect_sumR)
    chk("R_max", sR[-1] if sR else None, a.expect_R_max)
    if a.expect_R_p50 is not None:
        got = (quantile_nr(sR, .5), median_interp(sR))
        checks["R_p50"] = {"expected": a.expect_R_p50, "got_nearest_rank": got[0],
                           "got_interp": got[1], "ok": a.expect_R_p50 in got}
    ok = all(c["ok"] for c in checks.values())

    summary = {
        "tag": a.tag,
        "selfcheck": ("PASS" if ok else "FAIL") if checks else "NOT_RUN",
        "checks": checks,
        "matrix": {"nrows": nr, "ncols": nc, "nnz_input": nnz_in, "nnz_used": len(ent)},
        "windows": nwin, "rows_covered": nrow_used,
        "sumU": sum(Us), "sumR": sum(Rs), "sum_expected_instr_k": sum(instr),
        "U": dist(Us), "R": dist(Rs), "seg_len": dist(all_len), "seg_gap": dist(all_gap),
        "equi_groups": {
            "segments_total": nseg,
            "segments_by_bucket": bucket_seg,
            "fraction_by_bucket": {b: (v / nseg if nseg else None) for b, v in bucket_seg.items()},
        },
        "writeback": {
            "sum_segments_all_rows": sum(wb_all),
            "kappa_all_rows": sum(wb_all) / nwin if nwin else None,
        },
        "dedup": dedup,
    }
    if aiv is not None:
        summary["aiv"] = {"Z_total": sum(aivZ), "H_total": sum(aivH), "R_V_total": sum(aivR),
                          "Z_per_window": dist(aivZ), "H_per_window": dist(aivH),
                          "R_V_per_window": dist(aivR), "seg_len": dist(aiv_len),
                          "nnz_per_row": dist([len(rows[i]) for i in seq_rows if rows[i]])}
        summary["writeback"].update({
            "sum_segments_aiv": sum(wb_aiv), "sum_segments_aic": sum(wb_aic),
            "kappa_split": (sum(wb_aiv) + sum(wb_aic)) / nwin if nwin else None})

    meta = {
        "script_version": VERSION,
        "argv": sys.argv[1:],
        "rules": {"W": a.W, "k": a.k, "drop_diag": a.drop_diag, "tail": a.tail,
                  "index_base": a.index_base, "order_base": a.order_base, "symmetrize": a.symmetrize,
                  "col_order": a.col_order or "identity", "row_order": a.row_order or "identity"},
        "inputs_sha256": {"matrix": sha256_file(a.matrix),
                          "row_order": sha256_file(a.row_order) if a.row_order else None,
                          "col_order": sha256_file(a.col_order) if a.col_order and a.col_order != "same" else None,
                          "aiv_rows": sha256_file(a.aiv_rows) if a.aiv_rows else None,
                          "script": sha256_file(os.path.abspath(__file__))},
    }

    wcsv(P("windows.csv"), ["window", "row_first", "row_last", "nnz", "U", "R", "k_chunks",
                            "expected_instr_k", "seg_lens", "seg_gaps"], win_rows)
    wcsv(P("R_hist.csv"), ["R", "windows"], hist(Rs))
    wcsv(P("equi_groups.csv"), ["segs_in_group", "seg_len", "gap", "groups", "segments",
                                "m5_bucket", "exceeds_m5_count"], grp_rows)
    wcsv(P("chunks.csv"), ["window", "chunk", "rows", "segs", "seg_lens"], chunk_rows)
    if aiv is not None:
        wcsv(P("aiv_windows.csv"), ["window", "Z", "H", "R_V", "seg_lens"], aiv_rows_out)
    wb = [(w, wb_all[w]) + ((wb_aiv[w], wb_aic[w]) if aiv is not None else ()) for w in range(nwin)]
    wcsv(P("writeback.csv"), ["window", "segs_all_rows"] + (["segs_aiv", "segs_aic"] if aiv is not None else []), wb)
    with open(P("summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(P("meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    names = ["windows.csv", "R_hist.csv", "equi_groups.csv", "chunks.csv", "writeback.csv",
             "summary.json", "meta.json"] + (["aiv_windows.csv"] if aiv is not None else [])
    if ok:   # 自检不过不产出回放文件
        os.makedirs(P("replay"), exist_ok=True)
        wcsv(P("replay/segtable.csv"), ["window", "seg_start", "seg_len"], seg_table)
        wcsv(P("replay/fetch_seq.csv"), ["a_row", "b_row"], seq)
        names += ["replay/segtable.csv", "replay/fetch_seq.csv"]
    with open(P("SHA256SUMS"), "w", encoding="utf-8") as f:
        for n in sorted(names):
            f.write("%s  %s\n" % (sha256_file(P(n)), n))

    print("%s  窗口=%d  ΣU=%d  ΣR=%d  R_p50=%s  R_max=%s  自检=%s" % (
        a.tag, nwin, sum(Us), sum(Rs), quantile_nr(sR, .5), sR[-1] if sR else None, summary["selfcheck"]))
    if not ok:
        for k_, c in checks.items():
            if not c["ok"]:
                sys.stderr.write("自检不符 %s: %s\n" % (k_, json.dumps(c, ensure_ascii=False)))
        sys.exit(2)


if __name__ == "__main__":
    main()
