"""Export recorded process peaks without modifying the sealed first delivery."""
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from naming import t23_name

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / 'delivery/第一层实验结果/round1-compare-20261106'
PREFIX = BASE / 'delivery/round1-compare-20261106.post-memory-supplement'
KEYS = 'matrix member W seed diag tau placement d_rule source'.split()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(row):
    result = dict(row)
    result['member'] = t23_name(row['member'])
    return tuple(str(result[k]) for k in KEYS)


def run():
    outputs = [Path(str(PREFIX) + '.' + ext) for ext in ['csv', 'json', 'md', 'sha256']]
    assert not any(p.exists() for p in outputs), 'leave existing supplement unchanged'
    receipt = json.loads((BASE / 'delivery/round1-compare-20261106.receipt.json').read_text())
    records = {}
    for record_path in sorted((ROOT / 'logs/raw-post-e').glob('*/record.json')):
        record = json.loads(record_path.read_text())
        rows_path = record_path.parent / 'rows.json'
        if record.get('peak_mem_mb') is None or not rows_path.exists():
            continue
        for raw in json.loads(rows_path.read_text()):
            records.setdefault(key(raw), (raw, record, record_path, rows_path))
    exported = []
    comparisons = 'k_windows sumU T sumGamma sumR R_p50 R_p90 R_max d_sec'.split()
    for number, result in enumerate(csv.DictReader((ROOT / 'results.csv').open()), 2):
        if result['source'] != 'post-E':
            continue
        raw, record, record_path, rows_path = records[key(result)]
        assert not result['peak_mem_mb']
        for field in comparisons:
            assert Decimal(result[field]) == Decimal(str(raw[field])), (key(result), field)
        peak = record['peak_mem_mb']
        assert isinstance(peak, (float, int)) and peak > 0
        inherited = 'P-LS output reused from verified T21 order' in result['note']
        scope = 'actual current-run post process lifetime final peak, including LS/validation and all four layouts; shared by four condition rows'
        if inherited:
            scope += '; frozen T21 output has an identical validated order; this is validation-process peak, not historical T21 or reuse-only peak'
        row = {k: result[k] for k in KEYS}
        row.update(peak_mem_mb=peak, peak_mem_scope=scope,
                   frozen_T21_order_validation=inherited,
                   original_csv_line=number,
                   source_record_archive_path=record_path.relative_to(ROOT).as_posix(),
                   source_record_sha256=digest(record_path),
                   source_rows_archive_path=rows_path.relative_to(ROOT).as_posix(),
                   source_rows_sha256=digest(rows_path))
        exported.append(row)
    assert len(exported) == 896
    assert len({tuple(row[k] for k in KEYS) for row in exported}) == 896
    record_count = len({row['source_record_archive_path'] for row in exported})
    assert record_count == 224
    assert sum(row['frozen_T21_order_validation'] for row in exported) == 48
    with outputs[0].open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(exported[0]))
        writer.writeheader()
        writer.writerows(exported)
    proof = dict(passed=True, sealed_archive_sha256=receipt['sha256'],
                 original_results_sha256=digest(ROOT / 'results.csv'),
                 supplement_rows=len(exported), actual_post_process_records=record_count,
                 frozen_T21_validation_rows=48, source_metrics_compared=comparisons,
                 source_metric_comparisons=len(exported) * len(comparisons),
                 supplement_sha256=digest(outputs[0]),
                 original_sealed_files_modified=False,
                 memory_scope='recorded end-of-process ru_maxrss, not per-condition incremental memory or historical T21 peak')
    outputs[1].write_text(json.dumps(proof, indent=2) + '\n')
    outputs[2].write_text(
        '# T23 首包 post-E 峰值内存补充\n\n'
        '对应封存包 SHA-256 `' + receipt['sha256'] + '`，原包与原结果表未修改。\n\n'
        'CSV 对应原结果表的896条 post-E 条件，补出224个原始后处理进程最终记录的峰值内存（MiB）。'
        '每个进程的4条条件共享同一最终峰值，不能解释为每条条件的独立增量内存。'
        '字段标明原CSV行号、原包内 record.json/rows.json 路径及各自SHA-256；9个原始数值字段逐条与封存结果核对。\n\n'
        '其中48条对应12个T21冻结行序的本轮验证进程，其峰值包括本轮LS验证及布局，'
        '不代表T21历史峰值，也不代表单纯读取复用行序的峰值。没有重新运行实验或补造峰值。\n')
    outputs[3].write_text(''.join(digest(p) + '  ' + p.name + '\n' for p in outputs[:3]))
    print(json.dumps(proof), flush=True)


if __name__ == '__main__':
    run()
