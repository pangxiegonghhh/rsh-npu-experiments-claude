"""Keep complete intermediate Rabbit graph renumberings local, with byte ledgers.

This packages existing evidence only. It never runs Rabbit or computes metrics.
"""
import hashlib
import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
AUTHOR = 'f93776e9c1e1d4a8962ee56bc7ff0091e6fe12dd'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def validate_mapping(path, vertices):
    seen = bytearray(vertices)
    count = 0
    with Path(path).open('rb') as stream:
        for line in stream:
            value = int(line)
            assert 0 <= value < vertices and not seen[value], (path, count, value)
            seen[value] = 1
            count += 1
    assert count == vertices, (path, count, vertices)
    return count


def discover(base=BASE):
    base = Path(base)
    matrices = {r['matrix']: r for r in json.loads((base/'logs/matrices-and-taus.json').read_text())}
    found = []
    for matrix in ['reddit', 'ogbn-products']:
        for mode in ['B', 'U']:
            key = f'{matrix}-{mode}-repeat0'
            record_path = base/'work/rabbit-coarse'/(key+'.record.json')
            record = json.loads(record_path.read_text())
            mapping = Path(record['runtime_path'])
            assert mapping.resolve() == (base/'work/rabbit-coarse'/(key+'.mapping')).resolve()
            assert record['status'] == 'OK' and record['exitcode'] == 0
            assert record['key'] == key and record['author_ref'] == AUTHOR
            assert record['threads'] == 1 and record['actual_seed'] is None
            assert record['host_input_record']['matrix'] == matrix
            assert record['host_input_record']['mode'] == mode
            assert record['input_gz_sha256'] == record['host_input_record']['sha256']
            assert mapping.stat().st_size == record['mapping_bytes']
            assert sha(mapping) == record['mapping_sha256']
            n = int(matrices[matrix]['n'])
            found.append(dict(key=key, matrix=matrix, mode=mode, row_vertices=n,
                              graph_vertices=n*(2 if mode == 'B' else 1),
                              source_path=str(mapping), size=mapping.stat().st_size,
                              sha256=sha(mapping), record_path=str(record_path),
                              record_sha256=sha(record_path)))
    assert len(found) == 4
    return found


def install(root, name, base=BASE, selected=None, local_directory=None):
    root, base = Path(root), Path(base)
    all_sources = discover(base)
    sources = all_sources
    scope = 'all four original second-batch Rabbit graph mappings'
    if selected is not None:
        selected = set(selected)
        assert selected <= {r['key'] for r in all_sources}
        sources = [r for r in all_sources if r['key'] in selected]
        scope = 'explicit validation subset; not a full-install claim'
    ledger = root/'rabbit-coarse-manifest.json'
    assert not ledger.exists(), 'do not overwrite an existing evidence ledger'
    local = Path(local_directory) if local_directory is not None else base/'local-rabbit-coarse'/name
    assert not local.resolve().is_relative_to(root.resolve()), 'full mappings must stay outside archive root'
    local.mkdir(parents=True, exist_ok=True)
    records = root/'rabbit-coarse-records'
    records.mkdir(parents=True, exist_ok=True)
    files = []
    for source in sources:
        original = Path(source['source_path'])
        assert validate_mapping(original, source['graph_vertices']) == source['graph_vertices']
        target = local/(source['key']+'.'+source['sha256'][:12]+'.mapping')
        if not target.exists():
            shutil.copyfile(original, target)
        assert target.stat().st_size == source['size'] and sha(target) == source['sha256']
        assert sha(original) == source['sha256']
        record_copy = records/(source['key']+'.record.json')
        assert not record_copy.exists()
        shutil.copyfile(source['record_path'], record_copy)
        assert sha(record_copy) == source['record_sha256']
        files.append(dict(source, local_path=str(target), permutation_validated=True,
                          archived_record_path=record_copy.relative_to(root).as_posix(),
                          archived_record_sha256=sha(record_copy),
                          storage='complete intermediate graph permutation local-only; original record in archive'))
    result = dict(selection_scope=scope, raw_originals_local_only=True,
                  local_directory=str(local), file_count=len(files),
                  total_raw_bytes=sum(r['size'] for r in files),
                  all_available_raw_bytes=sum(r['size'] for r in all_sources),
                  expected_second_batch_mappings=4, files=files,
                  scientific_recomputation_performed=False,
                  policy='Intermediate Rabbit vertex renumberings contain full permutations (B has row+column vertices, U has rows). They follow the bulk-order local-only policy and do not inflate the count of new independent final A-row orders. Raw source records are copied unchanged; use this ledger for local mapping paths.')
    ledger.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    verify(root)
    return dict(file_count=len(files), total_raw_bytes=result['total_raw_bytes'],
                local_directory=str(local), raw_originals_local_only=True,
                manifest_path=ledger.name, manifest_sha256=sha(ledger),
                raw_copies_byte_verified=True, permutations_validated=True)


def verify(root):
    root = Path(root)
    assert not list(root.rglob('*.mapping')), 'complete coarse vectors leaked into archive root'
    ledger = json.loads((root/'rabbit-coarse-manifest.json').read_text())
    assert ledger['raw_originals_local_only'] is True
    assert ledger['file_count'] == len(ledger['files'])
    assert ledger['total_raw_bytes'] == sum(r['size'] for r in ledger['files'])
    for item in ledger['files']:
        original, local = Path(item['source_path']), Path(item['local_path'])
        assert not local.resolve().is_relative_to(root.resolve())
        assert sha(original) == sha(local) == item['sha256']
        assert original.stat().st_size == local.stat().st_size == item['size']
        record = root/item['archived_record_path']
        assert sha(record) == sha(item['record_path']) == item['record_sha256']
        assert sha(record) == item['archived_record_sha256']
        raw = json.loads(record.read_text())
        assert raw['mapping_sha256'] == item['sha256']
        assert raw['mapping_bytes'] == item['size'] and item['permutation_validated'] is True
    return dict(passed=True, files=ledger['file_count'], raw_bytes=ledger['total_raw_bytes'])
