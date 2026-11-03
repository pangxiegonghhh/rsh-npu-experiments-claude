"""Close a stopped, passing G3 run; preserve original binaries and final logs."""
from pathlib import Path
import hashlib
import json
import tarfile
import time


def close(root: Path, parent: Path) -> dict:
    assert (root / 'driver.rc').read_text().strip() == 'G3_RC=0'
    summary = json.loads((root / 'summary.json').read_text())
    assert summary['status'] == 'PASS' and summary['device_calls'] == 233
    assert summary['device_processes'] == 179 and summary['max_abs_error'] == 0
    checks = json.loads((root / 'checks.json').read_text())
    commands = json.loads((root / 'commands.json').read_text())
    assert len(checks) == len(commands) == 179
    assert all(x['status'] == 'PASS' and x['sequence_complete'] for x in checks)
    assert sum(x['iterations'] for x in checks) == 233
    assert all(x['returncode'] == 0 and x['end_unix'] >= x['start_unix'] for x in commands)
    checkpoint = json.loads((root / 'expected-parent-checkpoint.json').read_text())
    for name, want in {**checkpoint['source_sha256'], **checkpoint['binary_sha256']}.items():
        assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == want, name
    environment = json.loads((root / 'environment.json').read_text())
    resource = next(x['output'] for x in environment['commands'] if x['argv'][0].endswith('resource_query'))
    assert resource == checkpoint['resource_query']
    for name, want in checkpoint['binary_sha256'].items():
        data = (root / 'actual-artifacts' / name).read_bytes()
        assert data.startswith(b'\x7fELF') and hashlib.sha256(data).hexdigest() == want
    (root / 'closed.json').write_text(json.dumps({
        'status': 'PASS', 'closed_unix': time.time(), 'driver_rc': 0,
        'source_and_original_binaries_still_match_parent': True,
        'actual_original_ELF_files_saved': 6, 'resource_query_unchanged': True,
        'repeat_calls_individually_saved': 60, 'all_raw_calls_saved': 233,
        'E1_started': False}, indent=2) + '\n')
    files = sorted(p for p in root.rglob('*') if p.is_file()
                   and p.name != 'file-hashes.json' and '__pycache__' not in str(p))
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (root / 'file-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    archive = root.parent / (root.name + '-closed.tar.gz')
    with tarfile.open(archive, 'w:gz') as tf:
        for p in [*files, root / 'file-hashes.json']:
            tf.add(p, arcname=str(p.relative_to(root)), recursive=False)
    result = {'archive': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'bytes': archive.stat().st_size, 'members': len(files) + 1, 'status': 'PASS'}
    (root.parent / (root.name + '-closed-transfer.json')).write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(json.dumps(close(Path('/data/e0-g3-20261022-r1'), Path('/data/e0-supplement-r1'))), flush=True)
