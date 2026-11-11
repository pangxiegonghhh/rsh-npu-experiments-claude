"""Classify saved failed co-chain counts without running a scientific method.

Only byte-identified, reviewed producers justify claims about physical scans.
The reviewed producers use one matrix, one order and one W per process, evaluate
A0 before A1, and define both residual masks from A0. Equal threshold-mask
cardinalities therefore identify the same ordered D and K/window cache key.
"""
from pathlib import Path

PAIR_ERROR = 'co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE'
DIRECT_WRAPPERS = {
    '0927bfe6bd1f8d95855f4823ceb5ad657bc1f5e84233bf2ce3b0a4cdcf165794',
    'bcb8f4798830ee188b70668bb096239b63369430b4c952bf979cea55ce4adcb7',
    '3c24bf16a508de49d85eff37b0d68ad06aaf10133c2e5a41d0ad9852fced7e4d',
    '5ff24398f44ae2651d18e0ac42edce19977a7a5998d985ae0b742ba93b13fc19',
}
MEMO_WRAPPERS = {
    '7363e80fb095c6297d1e35113e9bf11e6a6ac05e354f5810ef65748b5f23b1e8',
    '3b7830ca38f2950d938f37de6539bd37fd8893dbfbbc8bca073ce9e019754c98',
}
PRODUCER_VERSIONS = {
    'scripts/evaluate_t23.py': {'33fad739a71e6a20847280c08f0b20af589a84d33f46d394053845bd785cf419'},
    'scripts/post_e_job.py': {
        '53f68b4087d536fa90aef408abf6bf534f5177d22b45c377fa2d9eae76254368',
        '5a57b975d55b39f84fb41cd3bc21f48e5b66a775140e8efafb61ac2b5061c299',
    },
    'scripts/recover_partial_post.py': {
        '4aa7b191452c2bd159b7c34d785a791fe2f9b1193b2667d6c96b27c4d962fc3a',
        '61e63be8cdf443c94dfe9fe49798b07e3629bb788575923c12698d3c90d9eb84',
    },
}


def is_failure_candidate(row):
    return (row.get('placement') == 'tail-co' and row.get('d_rule') == 'own'
            and PAIR_ERROR in row.get('note', ''))


def classify_failure(rows, index, command, residual_sizes):
    """Return an execution category, or None for an irrelevant failed row.

    residual_sizes comes from the actual immutable A0 degree array, not timings.
    Missing/unknown source evidence conservatively yields structural-only data.
    """
    row = rows[index]
    if not is_failure_candidate(row):
        return None
    sources = command.get('source_sha256', {})
    wrapper = sources.get('scripts/native.py')
    result = dict(guard_scan_execution='execution_unproven_structural_only',
                  native_wrapper_sha256=wrapper, observed_row_index=index,
                  cache_origin_row_index=None)
    if wrapper not in DIRECT_WRAPPERS | MEMO_WRAPPERS:
        result['execution_reason'] = 'unknown or missing wrapper version; no execution claim'
        return result
    entry = next(('scripts/' + Path(v).name for v in command.get('command', [])
                  if isinstance(v, str) and v.endswith('.py')), None)
    producer_sha = sources.get(entry)
    result.update(producer_entrypoint=entry, producer_source_sha256=producer_sha)
    if producer_sha not in PRODUCER_VERSIONS.get(entry, set()):
        result['execution_reason'] = 'producer order/matrix/cache scope has not been byte-verified'
        return result
    if wrapper in DIRECT_WRAPPERS:
        result.update(guard_scan_execution='executed_scan_recovered',
                      execution_reason='reviewed producer calls the reviewed direct native wrapper; guard scan completes before this pair-map error')
        return result
    try:
        size = residual_sizes[int(row['tau'])]
    except (ValueError, TypeError, KeyError):
        result['execution_reason'] = 'actual A0 residual-mask identity unavailable'
        return result
    if row.get('diag') == 'A1' and not any(
            x.get('diag') == 'A0' and str(x.get('tau')) == str(row.get('tau'))
            and x.get('placement') == 'tail-co' and x.get('d_rule') == 'own'
            for x in rows[:index]):
        result['execution_reason'] = 'A1 row lacks the required saved A0 prefix'
        return result
    for i, previous in enumerate(rows[:index]):
        if previous.get('placement') != 'tail-co' or previous.get('W') != row.get('W'):
            continue
        try:
            same_mask = residual_sizes[int(previous['tau'])] == size
        except (ValueError, TypeError, KeyError):
            result['execution_reason'] = 'earlier co-chain cache key cannot be reconstructed'
            return result
        if not same_mask:
            continue
        if 'co_chain_guard_windows_skipped' in previous:
            result['execution_reason'] = 'earlier same-key successful chain conflicts with a later cached failure'
            return result
        if is_failure_candidate(previous):
            result.update(guard_scan_execution='inherited_failure_cache_count',
                          cache_origin_row_index=i, cache_origin_diag=previous.get('diag'),
                          cache_origin_tau=previous.get('tau'),
                          execution_reason='reviewed failure-memo wrapper returned an earlier same-incidence error; this condition did not execute a new guard scan')
            return result
    result.update(guard_scan_execution='executed_scan_recovered',
                  execution_reason='reviewed producer has no earlier matching failed/successful cache entry; native cold scan preceded this pair-map error')
    return result
