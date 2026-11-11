"""Preserve stage3 post-E checkpoint originals locally and archive small ledgers.

Full checkpoint JSON contains a row permutation, so it remains local alongside
bulk order evidence. Archive sidecars are explicitly derived, never raw copies.
No candidate, layout, metric or local-search computation is performed here.
"""
import hashlib
import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
POST_METHODS = {'B0', 'B1', 'C9-Gorder', 'C9-S', 'C10-BP', 'C2-LSH',
                'C3-W1', 'C3-W4', 'C4-U', 'C4-T', 'C7-I', 'C1-J', 'C1-H',
                'C5', 'C5-U', 'C8-METIS'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def has_permutation_field(value):
    if isinstance(value, dict):
        return 'row_perm' in value or any(has_permutation_field(v) for v in value.values())
    if isinstance(value, list):
        return any(has_permutation_field(v) for v in value)
    return False


def discover(base=BASE):
    base = Path(base)
    planned = json.loads((base/'logs/stage3-planned-cases.json').read_text())
    matrices = {r['matrix']: r for r in json.loads((base/'logs/matrices-and-taus.json').read_text())}
    expected = {}
    for case in planned:
        if (case['scope'] != 'second batch' or case['method'] not in POST_METHODS
                or case.get('data_missing') or case['matrix'] not in matrices):
            continue
        for t in matrices[case['matrix']]['taus']:
            key = case['case_id'] + '__tau' + str(t['tau'])
            assert key not in expected
            expected[key] = dict(case_id=case['case_id'], matrix=case['matrix'],
                                 member=case['method'], W=int(case['W']),
                                 seed=int(case['seed']), tau=int(t['tau']),
                                 n=int(matrices[case['matrix']]['n']))
    sources, ignored = [], []
    for p in sorted((base/'work/post-e').glob('stage3-*/last-completed-sweep.checkpoint.json')):
        key = p.parent.name
        if key not in expected:
            ignored.append(dict(path=str(p), reason='outside dispatched second-batch post-E core grid'))
            continue
        sources.append(dict(expected[key], key=key, source_path=str(p),
                            command_path=str(base/'logs'/('stage3-post-'+key+'.command.json'))))
    return sources, expected, ignored


def terminal_command(path):
    path = Path(path)
    r = json.loads(path.read_text())
    assert r.get('status') != 'RUNNING' and r.get('ended_at') is not None, path
    assert r.get('method_started_at') is not None, path
    fields = ['status', 'exitcode', 'reason', 'method_started_at', 'ended_at',
              'actual_method_seconds', 'queue_seconds', 'method_limit_seconds']
    return dict(path=str(path), sha256=sha(path), **{k: r.get(k) for k in fields})


def install(root, name, base=BASE, selected=None, local_directory=None):
    root, base = Path(root), Path(base)
    sources, expected, ignored = discover(base)
    selection_scope = 'all dispatched available original checkpoints'
    if selected is not None:
        selected = set(selected)
        assert selected <= {r['key'] for r in sources}
        sources = [r for r in sources if r['key'] in selected]
        selection_scope = 'explicit validation subset; not a campaign-completion claim'
    local = Path(local_directory) if local_directory is not None else base/'local-checkpoints'/name
    assert not local.resolve().is_relative_to(root.resolve()), 'full permutations must stay outside the archive root'
    local.mkdir(parents=True, exist_ok=True)
    derived = root/'checkpoint-metadata'
    derived.mkdir(parents=True, exist_ok=True)
    manifest_path = root/'checkpoints-manifest.json'
    assert not manifest_path.exists(), 'checkpoint ledger already exists; do not rewrite sealed evidence'
    files = []
    for i, source in enumerate(sources):
        p = Path(source['source_path'])
        command = terminal_command(source['command_path'])
        data = p.read_bytes()
        raw_sha = hashlib.sha256(data).hexdigest()
        checkpoint = json.loads(data)
        pi = checkpoint['row_perm']
        assert len(pi) == source['n'] and all(type(v) is int for v in pi)
        assert sorted(pi) == list(range(source['n'])), p
        assert int(checkpoint['tau']) == source['tau'] and int(checkpoint['W']) == source['W']
        assert int(checkpoint['seed']) == source['seed'] and checkpoint['lam'] == 0
        history = checkpoint['history']
        assert history and [r['sweep'] for r in history] == list(range(len(history)))
        assert history[-1]['sumU'] == checkpoint['tracked_sumU']
        assert history[-1]['sumGamma'] == checkpoint['tracked_sumGamma']
        filename = f'{i:04d}__{source["key"]}__{raw_sha[:12]}.json'
        raw_copy = local/filename
        if raw_copy.exists():
            assert raw_copy.read_bytes() == data, raw_copy
        else:
            shutil.copyfile(p, raw_copy)
        assert sha(raw_copy) == raw_sha and sha(p) == raw_sha
        metadata = {k: v for k, v in checkpoint.items() if k != 'row_perm'}
        assert not has_permutation_field(metadata), 'unhandled nested permutation field'
        post_record = p.parent/'record.json'
        post_reference = None
        if post_record.exists():
            post = json.loads(post_record.read_text())
            post_reference = dict(path=str(post_record), sha256=sha(post_record),
                                  status=post.get('status'), order_path=post.get('order_path'))
        sidecar = dict(kind='derived checkpoint metadata; not raw original JSON',
                       row_permutation_omitted=True, raw_checkpoint_sha256=raw_sha,
                       raw_checkpoint_size=len(data), raw_checkpoint_source_path=str(p),
                       raw_checkpoint_local_path=str(raw_copy), permutation_length=len(pi),
                       permutation_canonical_sha256=hashlib.sha256(json.dumps(pi, separators=(',', ':')).encode()).hexdigest(),
                       checkpoint_metadata=metadata, original_command=command,
                       original_post_record=post_reference,
                       note='Checkpoint status/note records its historical pre-final-check state; consult the original terminal command/post record for final status. No UG or layout recomputation is performed by this packager.')
        target = derived/filename
        assert not target.exists()
        target.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2))
        files.append(dict(source, raw_checkpoint_sha256=raw_sha, raw_checkpoint_size=len(data),
                          raw_checkpoint_local_path=str(raw_copy), permutation_length=len(pi),
                          metadata_path=target.relative_to(root).as_posix(), metadata_sha256=sha(target),
                          original_command=command, original_post_record=post_reference,
                          storage='raw full permutation local-only; derived metadata in archive'))
    present = {r['key'] for r in sources}
    unavailable = []
    if selected is None:
        for key in sorted(set(expected) - present):
            path = base/'logs'/('stage3-post-'+key+'.command.json')
            r = json.loads(path.read_text()) if path.exists() else {}
            unavailable.append(dict(key=key, reason='no original completed-sweep checkpoint file',
                                    post_command_path=str(path) if path.exists() else None,
                                    post_command_sha256=sha(path) if path.exists() else None,
                                    post_command_status=r.get('status'), exitcode=r.get('exitcode'),
                                    original_reason=r.get('reason')))
    result = dict(selection_scope=selection_scope, raw_originals_local_only=True,
                  local_directory=str(local), file_count=len(files),
                  total_raw_bytes=sum(r['raw_checkpoint_size'] for r in files),
                  archived_metadata_bytes=sum((root/r['metadata_path']).stat().st_size for r in files),
                  expected_post_cases=len(expected), cases_without_checkpoint=unavailable,
                  ignored_out_of_scope_checkpoints=ignored, files=files,
                  policy='Full checkpoint JSON contains row permutations and is retained locally under the bulk-order policy; archive sidecars omit row_perm and are explicitly derived. Checkpoints do not count as new independent computed orders.',
                  scientific_recomputation_performed=False)
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    verify(root)
    return dict(file_count=result['file_count'], total_raw_bytes=result['total_raw_bytes'],
                archived_metadata_bytes=result['archived_metadata_bytes'],
                raw_originals_local_only=True, local_directory=str(local),
                manifest_path='checkpoints-manifest.json', manifest_sha256=sha(manifest_path),
                raw_copies_byte_verified=True, permutations_validated=True,
                missing_checkpoint_cases=len(unavailable), ignored_out_of_scope=len(ignored))


def verify(root):
    root = Path(root)
    manifest = json.loads((root/'checkpoints-manifest.json').read_text())
    assert manifest['raw_originals_local_only'] is True
    assert manifest['file_count'] == len(manifest['files'])
    assert manifest['total_raw_bytes'] == sum(x['raw_checkpoint_size'] for x in manifest['files'])
    for item in manifest['files']:
        original = Path(item['source_path'])
        local = Path(item['raw_checkpoint_local_path'])
        assert not local.resolve().is_relative_to(root.resolve())
        assert sha(original) == sha(local) == item['raw_checkpoint_sha256']
        assert original.stat().st_size == local.stat().st_size == item['raw_checkpoint_size']
        path = root/item['metadata_path']
        assert sha(path) == item['metadata_sha256']
        sidecar = json.loads(path.read_text())
        assert sidecar['row_permutation_omitted'] is True and not has_permutation_field(sidecar)
        assert sidecar['raw_checkpoint_sha256'] == item['raw_checkpoint_sha256']
        assert sidecar['permutation_length'] == item['n']
        raw_metadata = json.loads(original.read_text())
        permutation = raw_metadata.pop('row_perm')
        assert sidecar['permutation_canonical_sha256'] == hashlib.sha256(json.dumps(permutation, separators=(',', ':')).encode()).hexdigest()
        assert sidecar['checkpoint_metadata'] == raw_metadata
        assert sha(Path(item['command_path'])) == item['original_command']['sha256']
    return dict(passed=True, files=len(manifest['files']), raw_bytes=manifest['total_raw_bytes'],
                no_archived_permutations=True)
