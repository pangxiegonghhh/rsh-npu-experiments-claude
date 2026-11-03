"""CPU-only exact reconstruction of measured H-Skip / V0-R / V2-R inputs."""
from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys
import tempfile
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import hc_cases, hv_cases
from scripts.skip_cases import (VARIANTS, add_controls, digest, load_frozen,
    materialize, plans_for, save, smoke_cases, verify_case)


def copy_reconstructed(source: Path, target: Path) -> None:
    """Check every reconstructed byte against saved metadata before copying."""
    meta = json.loads((target / 'metadata.json').read_text())
    rebuilt = verify_case(source)
    assert rebuilt['files_sha256'] == meta['files_sha256'], str(target)
    assert (source / 'config.txt').read_bytes() == (target / 'config.txt').read_bytes()
    for key, expected in meta['files_sha256'].items():
        old = target / f'{key}.bin'
        if not old.exists() or digest(old) != expected:
            shutil.copyfile(source / f'{key}.bin', old)
    verify_case(target)


def restore_smoke_dependencies() -> None:
    """Compact archives keep small-case metadata; restore their source binaries."""
    prep = json.loads((ROOT / 'results/hv/smoke_preparation.json').read_text())
    bases = [ROOT / record['root'] / 'H-V' for record in prep['cases']]

    def complete(path: Path) -> bool:
        meta = json.loads((path / 'metadata.json').read_text())
        return all((path / f'{key}.bin').exists() and digest(path / f'{key}.bin') == expected
                   for key, expected in meta['files_sha256'].items())

    if not all(complete(path) for path in bases):
        with tempfile.TemporaryDirectory(prefix='restore-skip-hv-smokes-', dir=ROOT) as td:
            temp = Path(td)
            with patch.object(hv_cases, 'ROOT', temp):
                hv_cases.smoke_cases(temp / 'results/hv')
            for target in bases:
                copy_reconstructed(temp / target.relative_to(ROOT), target)
    tail = ROOT / 'cases_hc/smoke_tail_all_zero/N33/H-C'
    if not complete(tail):
        with tempfile.TemporaryDirectory(prefix='restore-skip-hc-smoke-', dir=ROOT) as td:
            temp = Path(td)
            (temp / 'cases_hv').symlink_to(ROOT / 'cases_hv', target_is_directory=True)
            (temp / 'results/hv').mkdir(parents=True)
            shutil.copyfile(ROOT / 'results/hv/smoke_preparation.json', temp / 'results/hv/smoke_preparation.json')
            with patch.object(hc_cases, 'ROOT', temp):
                hc_cases.smoke_cases(temp / 'results/hc')
            copy_reconstructed(temp / tail.relative_to(ROOT), tail)


def restore_formal(dest: Path) -> list[dict]:
    manifest = json.loads((dest / 'manifest.json').read_text())
    records = []
    for name, expected_input in manifest['inputs'].items():
        source = ROOT / 'inputs' / name
        assert digest(source) == expected_input
        a, order, split, old = load_frozen(source)
        pd = dest / 'plans' / source.stem
        stats = json.loads((pd / 'structure.json').read_text())
        route = json.loads((pd / 'routing.json').read_text())
        assert route['split'] == split
        assert digest(pd / 'routing.json') == stats['routing_sha256'] == old['routing_sha256']
        assert (pd / 'routing.json').read_bytes() == (ROOT / 'results/hv/plans' / source.stem / 'routing.json').read_bytes()
        assert digest(ROOT / 'results/v2/orders' / source.stem / 'order.bin') == manifest['orders'][source.stem] == route['order_sha256']
        plans = plans_for(a, order, split)
        for n in (16, 64, 256):
            base = ROOT / 'cases_v0' / source.stem / f'N{n}' / 'V0'
            base_meta = verify_case(base)
            stride = (n + 15) // 16 * 16
            b = np.fromfile(base / 'rhs.bin', np.float16).reshape(a.shape[1] + 1, stride)[:a.shape[1], :n]
            gold = np.fromfile(base / 'golden.bin', np.float32).reshape(a.shape[0], stride)[:, :n]
            hashes = {}
            for variant in VARIANTS:
                target = ROOT / 'cases_skip' / source.stem / f'N{n}' / variant
                meta = json.loads((target / 'metadata.json').read_text())
                assert meta['routing_sha256'] == stats['routing_sha256']
                for key in ('ptr', 'cols', 'values', 'rhs', 'golden'):
                    assert meta['files_sha256'][key] == base_meta['files_sha256'][key]
                materialize(a, plans[variant], b, gold, target, meta)
                hashes[variant] = digest(target / 'metadata.json')
            assert len({verify_case(ROOT / 'cases_skip' / source.stem / f'N{n}' / v)['files_sha256']['valid'] for v in VARIANTS}) == 1
            add_controls(ROOT / 'cases_skip' / source.stem / f'N{n}' / 'H-Skip', source.stem, n)
            records.append({'matrix': source.stem, 'n': n, 'variant_cases': 3, 'metadata_sha256': hashes})
            print('SKIP_RECOVERED_EXACT', source.stem, n, flush=True)
    assert len(records) == len(manifest['inputs']) * 3
    return records


def main() -> None:
    dest = ROOT / 'results/skip'
    records = restore_formal(dest)
    restore_smoke_dependencies()
    expected_meta = {str(p.relative_to(ROOT)): (digest(p), p.stat().st_mtime_ns)
                     for p in (ROOT / 'cases_skip').rglob('metadata.json') if 'smoke_' in str(p)}
    cases = smoke_cases(dest)
    for path, (expected_hash, modified) in expected_meta.items():
        assert digest(ROOT / path) == expected_hash
        assert (ROOT / path).stat().st_mtime_ns == modified, path
    save(dest / 'local_data_recovery.json', {'passed': True, 'configurations': len(records),
        'variant_cases': len(records) * 3, 'records': records, 'smoke_cases': len(cases),
        'smoke_variant_cases': len(cases) * 3, 'measured_metadata_preserved': True})


if __name__ == '__main__':
    main()
