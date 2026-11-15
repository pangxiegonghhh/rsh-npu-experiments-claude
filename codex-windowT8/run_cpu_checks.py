"""Recompute task statistics in scratch space, leaving evidence unchanged."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import tempfile

from verify_bundle import ROOT, verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='audit-output')
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    before = verify()
    with tempfile.TemporaryDirectory(prefix='codex-windowT8-audit-') as tmp:
        scratch = Path(tmp)
        m4 = scratch / 'M4'
        m4.mkdir()
        # M4 scripts write audit outputs; keep the archived package read-only.
        for script in ['audit_m4_recovered_statistics.py', 'audit_t8_command_tables.py']:
            shutil.copyfile(ROOT / 'M4' / script, m4 / script)
        for folder in ['t8-m4-20261114', 't8-m4-replay-20261115',
                       't8-m4-recovered-statistics-20261115']:
            shutil.copytree(ROOT / 'M4' / folder, m4 / folder)
        shutil.copytree(ROOT / 'shared/t8-cpu-prep-20261114',
                        scratch / 'shared/t8-cpu-prep-20261114')
        tasks = [
            ('M4-models', [sys.executable, '-X', 'utf8', str(m4 / 'audit_m4_recovered_statistics.py')]),
            ('command-tables', [sys.executable, '-X', 'utf8', str(m4 / 'audit_t8_command_tables.py')]),
            ('M5-statistics', [sys.executable, '-X', 'utf8',
                               str(ROOT / 'M5/audit_m5_statistics_offline.py'),
                               str(ROOT / 'M5/t8-m5-evidence-20261115/t8-m5')]),
            ('M8-statistics', [sys.executable, '-X', 'utf8',
                               str(ROOT / 'M8/audit_m8_results.py'),
                               str(ROOT / 'M8/t8-m8-results-20261115'),
                               '--out', str(out / 'M8-statistics.json')]),
        ]
        results = []
        for name, cmd in tasks:
            log = out / (name + '.log')
            with log.open('w', encoding='utf-8') as stream:
                result = subprocess.run(cmd, cwd=scratch, stdout=stream, stderr=subprocess.STDOUT)
            results.append(dict(check=name, returncode=result.returncode, log=log.name))
            print(name, 'PASS' if result.returncode == 0 else 'FAIL', flush=True)
            if result.returncode:
                raise RuntimeError(name + ' failed; see ' + str(log))
        for file in [m4 / 't8-m4-recovered-statistics-20261115/model-recomputation-verification.json',
                     m4 / 't8-command-table-independent-audit-20261115.json']:
            if file.exists():
                shutil.copyfile(file, out / file.name)
    after = verify()
    assert before == after
    result = dict(status='PASS', package=after, checks=results, evidence_unchanged=True)
    (out / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
