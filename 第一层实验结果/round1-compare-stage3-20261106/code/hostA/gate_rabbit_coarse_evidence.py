"""Check local-only packaging on real Rabbit mappings; never run science."""
import json
import shutil
import tempfile
import time
from pathlib import Path
from rabbit_coarse_evidence import BASE, discover, install, sha, validate_mapping, verify


def rejected(function):
    try:
        function()
    except AssertionError:
        return True
    raise AssertionError('invalid evidence/policy accepted')


def main():
    sources = discover()
    assert len(sources) == 4 and sum(r['size'] for r in sources) == 61224521
    assert sum(r['size'] for r in sources) > 50*2**20
    selected = {'reddit-B-repeat0', 'ogbn-products-U-repeat0'}
    original = {r['source_path']: sha(r['source_path']) for r in sources}
    real = []
    with tempfile.TemporaryDirectory(prefix='rabbit-evidence-gate-', dir=BASE/'work') as directory:
        temp = Path(directory)
        root = temp/'archive'; root.mkdir()
        info = install(root, 'validation-subset', selected=selected, local_directory=temp/'local')
        assert info['file_count'] == 2 and info['raw_copies_byte_verified']
        ledger = json.loads((root/'rabbit-coarse-manifest.json').read_text())
        assert ledger['selection_scope'].startswith('explicit validation subset')
        assert not list(root.rglob('*.mapping'))
        for item in ledger['files']:
            assert item['graph_vertices'] == item['row_vertices']*(2 if item['mode']=='B' else 1)
            assert sha(item['source_path']) == sha(item['local_path']) == item['sha256']
            record = root/item['archived_record_path']
            assert record.read_bytes() == Path(item['record_path']).read_bytes()
            real.append({k: item[k] for k in ['key','graph_vertices','row_vertices','size','sha256']})
        target = Path(ledger['files'][0]['local_path'])
        good = target.read_bytes(); target.write_bytes(good+b' ')
        mapping_tamper = rejected(lambda: verify(root))
        target.write_bytes(good); assert verify(root)['passed']
        target = root/ledger['files'][0]['archived_record_path']
        good = target.read_bytes(); target.write_bytes(good+b' ')
        record_tamper = rejected(lambda: verify(root))
        target.write_bytes(good); assert verify(root)['passed']
        overwrite = rejected(lambda: install(root, 'validation-subset', selected=selected, local_directory=temp/'local'))
        wrong = temp/'wrong-archive'; wrong.mkdir()
        policy = rejected(lambda: install(wrong, 'bad', selected=selected, local_directory=wrong/'vectors'))
        invalid = temp/'invalid.mapping'
        for content in ['0\n1\n1\n', '0\n1\n3\n', '0\n1\n']:
            invalid.write_text(content)
            rejected(lambda: validate_mapping(invalid, 3))
        leak = root/'leaked.mapping'; leak.write_text('0\n')
        leak_check = rejected(lambda: verify(root)); leak.unlink()
        assert verify(root)['passed']
    for path, digest in original.items():
        assert sha(path) == digest, 'original mapping modified'
    baseline = json.loads((BASE/'logs/stage3-rabbit-coarse-evidence-before.json').read_text())
    for path, digest in baseline['scientific_sources_before'].items():
        assert sha(BASE/path) == digest, 'scientific source/binary changed'
    names = ['rabbit_coarse_evidence.py', 'gate_rabbit_coarse_evidence.py', 'build_stage3.py']
    for name in names:
        compile((BASE/'scripts'/name).read_text(), name, 'exec')
    result = dict(passed=True, at_utc=time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                  scope='metadata-only packaging gate on two real original mappings; no Rabbit/NN/LS/layout/UG recomputation',
                  implementation_sources={f'scripts/{name}':sha(BASE/'scripts'/name) for name in names},
                  global_original_files=4, global_original_bytes=61224521, real_mapping_checks=real,
                  tampered_mapping_rejected=mapping_tamper, tampered_record_rejected=record_tamper,
                  ledger_overwrite_rejected=overwrite, raw_vectors_inside_archive_rejected=policy,
                  archive_leak_rejected=leak_check, invalid_permutation_fixtures_rejected=3,
                  original_mapping_bytes_unchanged=True, scientific_sources_unchanged=True,
                  full_campaign_install_pending=True)
    (BASE/'logs/stage3-rabbit-coarse-evidence-gate.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(passed=True, real_mappings=2, both_B_and_U=True,
                          both_matrices=True, original_bytes_unchanged=True, scientific_reruns=False)))


if __name__ == '__main__':
    main()
