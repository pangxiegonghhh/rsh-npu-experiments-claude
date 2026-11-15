"""Run only after the full correctness gate. Keep timing records and rejected blocks."""
import csv
import json
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'm4-manifest.json').read_text())
points = [r for r in manifest if 'alias_of' not in r]
selected = [r for r in points if r['family'] == 'core' and r['dtype'] == 'FP16'
            and r['n'] == 16 and r['gap'] == 2 and r['r'] in (1, 32, 64)]
sentinel = next(r for r in points if r['name'] ==
                'core-u64-r16-n16-FP16-cold-gap2-split-g2')
selected.append(sentinel)
pilot_list = root / 'pilot.list'
pilot_list.write_text(''.join(r['name'] + '\n' for r in selected))
while not (root / 'check-v5.rc').exists():
    time.sleep(5)
assert (root / 'check-v5.rc').read_text().strip() == '0', 'Full correctness failed'
assert 'M4_ALL_PASS 2592 mode=check' in (root / 'check-v5.log').read_text()
records = []
for block in range(5):
    output = root / 'results-pilot-v5' / f'b{block:02d}'
    log = root / f'pilot-v5-b{block:02d}.log'
    start = time.monotonic()
    with log.open('w') as f:
        rc = subprocess.run([str(root / 'build/t8_micro'), 'timeblock', str(output),
                             str(block), str(pilot_list)], cwd=root, stdout=f,
                            stderr=subprocess.STDOUT).returncode
    elapsed = time.monotonic() - start
    assert rc == 0, f'Pilot block {block} failed; see {log}'
    registration = list(csv.DictReader((output / 'group-registration.csv').open()))
    valid = all(r['valid'] == '1' and r['input_immutable'] == '1' for r in registration)
    record = dict(block=block, wall_seconds=elapsed, valid=valid,
                  cases=len(list(csv.DictReader((output / 'timing.csv').open()))),
                  registration=registration)
    records.append(record)
    (root / 'pilot-v5-summary.json').write_text(json.dumps(records, indent=2))
    print(json.dumps(record), flush=True)
print('PILOT_COMPLETE', flush=True)
