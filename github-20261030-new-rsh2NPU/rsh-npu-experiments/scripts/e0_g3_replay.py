"""Read-only independent local replay of the closed G3 archive."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import numpy as np


def replay(root: Path) -> dict:
    manifest = json.loads((root / 'inputs/manifest.json').read_text())['cases']
    references = {}
    basis = {x['case_id']: x for x in json.loads((root / 'physical-basis.json').read_text())}
    for info in manifest:
        case = root / 'inputs' / info['id']; c = info['config']; mp, kp, npad = c[3:6]
        for name, want in info['sha256'].items():
            assert hashlib.sha256((case / name).read_bytes()).hexdigest() == want
        a = np.fromfile(case / 'a.bin', dtype='<f2').reshape(mp, kp).astype(np.float64)
        refs = np.fromfile(case / 'refs.bin', dtype='<i4')
        b = np.fromfile(case / 'b.bin', dtype='<f2').reshape(-1, npad).astype(np.float64)
        oracle = (a @ b[refs]).astype('<f4')
        assert oracle.tobytes() == (case / 'golden.bin').read_bytes(), info['id']
        if info['id'] in basis:
            raw = (case / 'a-direct.bin').read_bytes()
            expected = bytearray(len(raw))
            for slot in basis[info['id']]['slots']:
                r, k = slot['row'], slot['logical_k']
                assert slot['byte_offset'] == (k // 16) * 512 + r * 32 + (k % 16) * 2
                assert a[r, k] == 1
                struct.pack_into('<H', expected, slot['byte_offset'], 0x3c00)
            assert raw == expected
        references[info['id']] = (oracle, info)
    records = json.loads((root / 'checks.json').read_text())
    total = 0; groups = {}; maximum = 0.0
    for record in records:
        name = record['case_id']; group = record['group']; dest = root / 'results' / group / name
        count = record['iterations']; host = json.loads((dest / 'host.json').read_text())
        assert host['iterations'] == count and host['status'] == 'SYNC_OK'
        for prefix in ('output', 'debug'):
            assert sorted(int(x.stem.split('-')[-1]) for x in dest.glob(prefix + '-*.bin')) == list(range(count))
        oracle, info = references[name]; guard = host['guard_byte']
        for i in range(count):
            raw = (dest / f'output-{i}.bin').read_bytes()
            assert len(raw) == oracle.nbytes + 2048
            assert raw[:1024] == raw[-1024:] == bytes([guard]) * 1024
            actual = np.frombuffer(raw[1024:-1024], dtype='<f4').reshape(oracle.shape)
            expected = -oracle if (i % 2 + (i // 2) % 2) % 2 else oracle
            assert np.isfinite(actual).all() and np.array_equal(actual, expected), (name, group, i)
            maximum = max(maximum, float(np.max(np.abs(actual - expected))))
            debug = (dest / f'debug-{i}.bin').read_bytes()
            assert debug[:1024] == debug[-1024:] == bytes([guard]) * 1024
            assert struct.unpack('<4i', debug[1024:-1024]) == tuple([info['mmad_calls'], *info['expected_mmad']])
            total += 1
        groups[group] = groups.get(group, 0) + 1
    assert groups['B-independent'] == 144 and groups['A-confirmed-B'] == 24
    assert groups['physical-anchor'] == 1 and total == 233
    binaries = json.loads((root / 'expected-parent-checkpoint.json').read_text())['binary_sha256']
    for name, want in binaries.items():
        file = root / 'actual-artifacts' / name
        assert file.read_bytes()[:4] == b'\x7fELF'
        assert hashlib.sha256(file.read_bytes()).hexdigest() == want
    hashes = json.loads((root / 'file-hashes.json').read_text())
    for name, want in hashes.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == want, name
    return {'status': 'PASS', 'references_independently_recomputed': len(references),
            'physical_basis_cases_rechecked': len(basis), 'raw_device_calls_replayed': total,
            'device_process_groups': len(records), 'groups': groups,
            'actual_original_ELF_files_verified': len(binaries), 'member_hashes_verified': len(hashes),
            'maximum_absolute_error': maximum, 'raw_evidence_modified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('root', type=Path)
    print(json.dumps(replay(parser.parse_args().root), indent=2))
