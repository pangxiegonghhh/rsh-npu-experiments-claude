"""E0 G3: independent physical A basis, strict records, and immutable evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import time

import numpy as np
from e0_supplement import check_guard, check_output, write_json


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sequence(output: Path) -> int:
    meta = json.loads((output / 'host.json').read_text())
    count = meta['iterations']
    if meta['status'] != 'SYNC_OK' or not isinstance(count, int) or not 1 <= count <= 100:
        raise ValueError('Invalid synchronized iteration metadata')
    for prefix in ('output', 'debug'):
        found = sorted(int(p.stem.split('-')[-1]) for p in output.glob(prefix + '-*.bin'))
        if found != list(range(count)):
            raise ValueError(f'{prefix}: expected {list(range(count))}, got {found}')
    return count


def validate(case: Path, output: Path, direct: bool, requested: int) -> dict:
    count = sequence(output)
    assert count == requested, (count, requested)
    info = json.loads((case / 'case.json').read_text())
    c = info['config']; shape = (c[3], c[5])
    expected = np.fromfile(case / 'golden.bin', dtype='<f4').reshape(shape)
    mask = np.fromfile(case / 'mask.bin', dtype='u1').reshape(shape).astype(bool)
    guard = json.loads((output / 'host.json').read_text())['guard_byte']
    checks = []
    for i in range(count):
        ref = expected if (i % 2 + (i // 2) % 2) % 2 == 0 else -expected
        ck = check_output((output / f'output-{i}.bin').read_bytes(), ref, mask, guard)
        raw = (output / f'debug-{i}.bin').read_bytes()
        debug = np.frombuffer(raw[1024:-1024], dtype='<i4').tolist()
        assert check_guard(raw, 16, guard) == 0
        assert debug == [info['mmad_calls'], *info['expected_mmad']], debug
        assert ck['value_errors'] == ck['guard_errors'] == 0, ck
        checks.append({**ck, 'iteration': i, 'debug': debug, 'status': 'PASS'})
    for key in ('a', 'b', 'refs', 'config'):
        original = (case / ('a-direct.bin' if key == 'a' and direct else key + '.bin')).read_bytes()
        if (key == 'a' and ((count - 1) // 2) % 2) or (key == 'b' and (count - 1) % 2):
            words = np.frombuffer(original, dtype='<u2').copy(); words ^= 0x8000
            original = words.tobytes()
        raw = (output / (key + '-after.bin')).read_bytes()
        assert check_guard(raw, len(original), guard) == 0
        assert raw[1024:-1024] == original, key
    return {'case_id': info['id'], 'status': 'PASS', 'path': 'direct' if direct else 'normal',
            'iterations': count, 'sequence_complete': True, 'checks': checks,
            'max_abs_error': max(x['max_abs_error'] for x in checks)}


def selfcheck() -> dict:
    outcomes = []
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp); write_json(p / 'host.json', {'status': 'SYNC_OK', 'iterations': 2})
        for prefix in ('output', 'debug'):
            for i in range(2): (p / f'{prefix}-{i}.bin').write_bytes(b'')
        assert sequence(p) == 2
        for name in ('output-1.bin', 'debug-1.bin'):
            (p / name).unlink()
            try: sequence(p)
            except ValueError: outcomes.append(name + ': REJECT')
            else: raise AssertionError('Missing file accepted')
            (p / name).write_bytes(b'')
        (p / 'output-1.bin').rename(p / 'output-2.bin')
        try: sequence(p)
        except ValueError: outcomes.append('iteration gap: REJECT')
        else: raise AssertionError('Gap accepted')
    return {'complete_sequence': 'PASS', 'missing_and_gap_checks': outcomes}


def ranges(c: list[int], refs: np.ndarray, b_bytes: int) -> dict:
    mp, kp, npad = c[3:6]; kb, nb = kp // 16, npad // 16
    assert mp == 16 and c[7] == 0 and c[9] == 0
    b1_slots = []; b2_slots = []; transfers = []
    for r, row in enumerate(refs):
        for ni in range(nb):
            src = (int(row) * npad + ni * 16) * 2
            dst = ((r // 16 * nb + ni) * 256 + (r % 16) * 16) if c[6] else ((ni * kb + r // 16) * 256 + (r % 16) * 16)
            assert 0 <= src and src + 32 <= b_bytes
            b1_slots.extend(range(dst, dst + 16))
            transfers.append({'op': 'B_GM_L1', 'src_byte': src, 'dst_byte': dst * 2, 'bytes': 32})
    assert sorted(b1_slots) == list(range(kp * npad))
    for ki in range(kb):
        for ni in range(nb):
            src = (ki * nb + ni) * 512 if c[6] else (ni * kb + ki) * 512
            dst = (ki * nb + ni) * 512
            assert src + 512 <= kp * npad * 2 and dst + 512 <= kp * npad * 2
            b2_slots.extend(range(dst // 2, dst // 2 + 256))
            transfers.append({'op': 'B_L1_L0B', 'src_byte': src, 'dst_byte': dst, 'bytes': 512, 'transpose': True})
    assert sorted(b2_slots) == list(range(kp * npad))
    for ki in range(kb):
        transfers.append({'op': 'A_GM_L0A_reference', 'src_byte': ki * 512, 'dst_byte': ki * 512, 'bytes': 512, 'repeat': 1, 'transpose': False})
    return {'status': 'HOST_ENUMERATED', 'transfers': transfers,
            'L1_bytes': mp * kp * 2 + kp * npad * 2, 'L0A_bytes': mp * kp * 2,
            'L0B_bytes': kp * npad * 2, 'L0C_bytes': mp * npad * 4,
            'alignment_evidence': 'allocator contract and enumerated offsets; no raw L0 dump'}


def prepare(parent: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    items = json.loads((parent / 'inputs/manifest.json').read_text())['cases']
    selected = [x for x in items if x['id'].startswith(('A-selector_', 'B-selector_')) or x['id'] in ('control_K16_N16', 'control_K48_N64')]
    assert len(selected) == 170
    basis = []; addresses = []; new = []
    for old in selected:
        name = old['id']; src = parent / 'inputs' / name; dst = out / 'inputs' / name
        shutil.copytree(src, dst, dirs_exist_ok=False)
        info = json.loads((dst / 'case.json').read_text())
        if name.startswith('B-selector_'):
            c = info['config']; c[9] = 0
            np.asarray(c, dtype='<i4').tofile(dst / 'config.bin')
            tile = int(re.search(r'_s(\d+)$', name).group(1)); physical = bytearray(c[3] * c[4] * 2)
            slots = []
            # Literal W16 ZZ physical slots, not the normal ND2NZ packing helper.
            for row in range(16):
                offset = tile * 512 + row * 32 + row * 2
                struct.pack_into('<H', physical, offset, 0x3c00)
                slots.append({'row': row, 'logical_k': tile * 16 + row, 'byte_offset': offset, 'bits': '0x3c00'})
            assert (src / 'a-direct.bin').read_bytes() == physical
            (dst / 'a-direct.bin').write_bytes(physical)
            refs = np.fromfile(dst / 'refs.bin', dtype='<i4')
            b = np.fromfile(dst / 'b.bin', dtype='<f2').reshape(-1, c[5])
            expected = np.zeros((16, c[5]), dtype='<f4')
            for row in range(16): expected[row] = b[int(refs[tile * 16 + row])]
            assert expected.tobytes() == (dst / 'golden.bin').read_bytes()
            # A-only fixed basis cannot hide the old shared permutation counterexample.
            if c[4] >= 32 and tile == 0 and '_element_' in name:
                perm = np.arange(c[4]); perm[[0, 17]] = perm[[17, 0]]
                wrong = b[refs][perm][:16].astype('<f4')
                assert not np.array_equal(wrong, expected)
            basis.append({'case_id': name, 'slots': slots, 'A_sha256': sha(dst / 'a-direct.bin'),
                          'reference': 'literal raw FP16 basis; scalar B_global[refs[tile*16+r],n] oracle'})
            addresses.append({'case_id': name, **ranges(c, refs, b.nbytes)})
            info['g3_config_diff'] = {'index': 9, 'old': old['config'][9], 'new': 0}
        info['parent_case_json_sha256'] = sha(src / 'case.json')
        info['sha256'] = {p.name: sha(p) for p in dst.glob('*.bin')}
        write_json(dst / 'case.json', info); new.append(info)
    write_json(out / 'inputs/manifest.json', {'schema': 'e0-g3-independent-v1', 'cases': new})
    write_json(out / 'physical-basis.json', basis); write_json(out / 'address-ranges.json', addresses)
    write_json(out / 'sequence-selfcheck.json', selfcheck())
    write_json(out / 'preflight.json', {'status': 'PASS', 'B_cases': len(basis), 'A_cases': 24,
               'CXX_kernel_changed': False, 'parent_manifest_sha256': sha(parent / 'inputs/manifest.json'),
               'counterexample_rejected_with_fixed_A': True})
    print('LOCAL_PREFLIGHT_PASS', len(basis), 'B references; 24 A cases; sequence selfcheck passed')


def run(parent: Path, out: Path) -> None:
    checkpoint = json.loads((parent / 'manifest-checkpoint.json').read_text())
    assert checkpoint == json.loads((out / 'expected-parent-checkpoint.json').read_text())
    for key in ('source_sha256', 'binary_sha256'):
        for name, want in checkpoint[key].items(): assert sha(parent / name) == want, name
    headers = json.loads((parent / 'sdk-header-hashes.json').read_text())
    assert headers == json.loads((out / 'expected-sdk-headers.json').read_text())
    for name, want in headers.items(): assert sha(Path(name)) == want, name
    write_json(out / 'parent-verified.json', {'checkpoint': checkpoint, 'sdk_headers': headers, 'status': 'PASS'})
    # Recover the actual original executables/libraries, not just hash manifests.
    saved = out / 'actual-artifacts'; saved.mkdir()
    for name in checkpoint['binary_sha256']:
        dst = saved / name; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(parent / name, dst)
    for name in ('integrated-final/lib/librsh_kernels.a', 'repeat-each', 'resource_query'):
        if (parent / name).is_file():
            dst = saved / name; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(parent / name, dst)
    commands = []; records = []
    def invoke(name: str, mode: str, group: str, iterations: int = 1) -> None:
        dest = out / 'results' / group / name; dest.mkdir(parents=True)
        argv = [str(parent / 'build-final' / ('e0_' + mode)), str(out / 'inputs' / name), str(dest), mode, str(iterations)]
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cmd = {'argv': argv, 'pid': process.pid, 'start_unix': time.time(), 'group': group}
        commands.append(cmd); write_json(out / 'commands.json', commands)
        try: log, _ = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill(); log, _ = process.communicate(); (dest / 'run.log').write_bytes(log); raise
        (dest / 'run.log').write_bytes(log)
        cmd.update({'returncode': process.returncode, 'end_unix': time.time()})
        write_json(out / 'commands.json', commands)
        assert process.returncode == 0, (name, process.returncode, log[-2000:])
        result = validate(out / 'inputs' / name, dest, mode == 'direct', iterations)
        result['group'] = group; records.append(result)
        write_json(out / 'checks.json', records)
        print(group, name, result['status'], iterations, flush=True)
    invoke('B-selector_K16_N16_l1_b0_element_s0', 'direct', 'physical-anchor')
    for name in ('control_K16_N16', 'control_K48_N64'):
        for mode in ('normal', 'direct'): invoke(name, mode, 'controls-' + mode)
    cases = json.loads((out / 'inputs/manifest.json').read_text())['cases']
    for info in cases:
        if info['id'].startswith('B-selector_'): invoke(info['id'], 'direct', 'B-independent')
    for info in cases:
        if info['id'].startswith('A-selector_'): invoke(info['id'], 'normal', 'A-confirmed-B')
    for rep in range(3):
        for layout in (0, 1): invoke(f'B-selector_K48_N64_l{layout}_b1_element_s2', 'direct', f'core-repeat-{rep}', 10)
    summary = {'status': 'PASS', 'B_independent_cases': 144, 'A_regression_cases': 24,
               'anchor_cases': 1, 'control_cases': 4, 'repeat_processes': 6, 'repeat_calls': 60,
               'device_processes': len(records), 'device_calls': sum(x['iterations'] for x in records),
               'max_abs_error': max(x['max_abs_error'] for x in records), 'end_unix': time.time(),
               'CXX_source_and_binaries_unchanged': True, 'physical_reference': 'A direct, repeat=1, bulk=0'}
    write_json(out / 'summary.json', summary)
    hashes = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file() and '__pycache__' not in str(p)}
    write_json(out / 'file-hashes.json', hashes)
    archive = out.parent / (out.name + '-evidence.tar.gz')
    with tarfile.open(archive, 'w:gz') as tf:
        for name in [*hashes, 'file-hashes.json']: tf.add(out / name, arcname=name, recursive=False)
    transfer = {'archive': archive.name, 'bytes': archive.stat().st_size, 'sha256': sha(archive)}
    write_json(out.parent / (out.name + '-transfer.json'), transfer)
    print('G3_FINAL_PASS', json.dumps(summary), json.dumps(transfer), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'run', 'selfcheck'])
    parser.add_argument('--parent', type=Path); parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.action == 'selfcheck': print(json.dumps(selfcheck())); return
    if not args.parent or not args.out: parser.error('--parent and --out are required')
    if args.action == 'prepare': prepare(args.parent.resolve(), args.out.resolve())
    else: run(args.parent.resolve(), args.out.resolve())


if __name__ == '__main__': main()
