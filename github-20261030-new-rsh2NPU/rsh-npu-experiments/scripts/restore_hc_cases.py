"""Restore exact measured H-C binaries on CPU from saved ownership and metadata."""
from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsh.planner import layout
from rsh.prepare import export
from scripts.hc_cases import add_controls, digest, load_frozen, save, verify_case


def main() -> None:
    dest = ROOT/'results/hc'
    manifest = json.loads((dest/'manifest.json').read_text())
    records = []
    for name, expected_input in manifest['inputs'].items():
        source = ROOT/'inputs'/name
        assert digest(source) == expected_input
        a, order, split, hvstats = load_frozen(source)
        pd = dest/'plans'/source.stem
        stats = json.loads((pd/'structure.json').read_text())
        route = json.loads((pd/'routing.json').read_text())
        assert route['split'] == split
        assert digest(pd/'routing.json') == stats['routing_sha256'] == hvstats['routing_sha256']
        assert digest(ROOT/'results/v2/orders'/source.stem/'order.bin') == manifest['orders'][source.stem] == route['order_sha256']
        plan = layout(a, order, split, 'H-C')
        for n in (16, 64, 256):
            target = ROOT/'cases_hc'/source.stem/f'N{n}'/'H-C'
            meta = json.loads((target/'metadata.json').read_text())
            assert meta['routing_sha256'] == stats['routing_sha256']
            expected = meta['files_sha256']
            base = ROOT/'cases_v0'/source.stem/f'N{n}'/'V0'
            base_meta = verify_case(base)
            for key in ('ptr', 'cols', 'values', 'rhs', 'golden', 'valid'):
                assert expected[key] == base_meta['files_sha256'][key]
            if not all((target/f'{key}.bin').exists() and digest(target/f'{key}.bin') == h for key, h in expected.items()):
                stride = (n+15)//16*16
                b = np.fromfile(base/'rhs.bin', np.float16).reshape(a.shape[1]+1, stride)[:a.shape[1], :n]
                gold = np.fromfile(base/'golden.bin', np.float32).reshape(a.shape[0], stride)[:, :n]
                with tempfile.TemporaryDirectory(prefix='restore-hc-', dir=ROOT) as tmp:
                    temporary = Path(tmp)
                    export(a, plan, b, gold, temporary, meta)
                    for key, h in expected.items():
                        assert digest(temporary/f'{key}.bin') == h, (name, n, key)
                    # Regenerate config exactly, but preserve measured metadata.
                    if (target/'config.txt').exists():
                        assert (temporary/'config.txt').read_bytes() == (target/'config.txt').read_bytes()
                    for path in temporary.iterdir():
                        if path.name != 'metadata.json':
                            shutil.move(str(path), target/path.name)
            verify_case(target)
            add_controls(target, source.stem, n)
            records.append({'matrix': source.stem, 'n': n, 'verified_files': len(expected)})
            print('HC_RECOVERED_EXACT', source.stem, n, flush=True)
    assert len(records) == len(manifest['inputs'])*3 == 24
    save(dest/'local_data_recovery.json', {'passed': True, 'configurations': len(records), 'records': records})


if __name__ == '__main__':
    main()
