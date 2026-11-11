"""Validate evidence packaging on two saved, terminal checkpoints; no reruns."""
import hashlib
import json
import tempfile
import time
from pathlib import Path

from checkpoint_evidence import (BASE, discover, has_permutation_field, install,
                                 sha, terminal_command, verify)


def main():
    selected = {'stage3-reddit__C4-U__W16__seed0__tau153',
                'stage3-reddit__C3-W4__W16__seed0__tau153'}
    sources, expected, ignored = discover()
    assert len(expected) == 64
    assert selected <= {r['key'] for r in sources}
    original = {r['key']: dict(path=r['source_path'], sha256=sha(r['source_path']))
                for r in sources if r['key'] in selected}
    for key in selected:
        command = terminal_command(next(r['command_path'] for r in sources if r['key'] == key))
        assert command['exitcode'] == (124 if 'C4-U' in key else 0)
    checks = []
    with tempfile.TemporaryDirectory(prefix='checkpoint-evidence-gate-', dir=BASE/'work') as directory:
        temp = Path(directory)
        root = temp/'archive-staging'; root.mkdir()
        info = install(root, 'validation-subset', selected=selected, local_directory=temp/'local-originals')
        ledger = json.loads((root/'checkpoints-manifest.json').read_text())
        assert info['file_count'] == 2 and info['raw_copies_byte_verified']
        assert ledger['selection_scope'].startswith('explicit validation subset')
        for item in ledger['files']:
            source = Path(item['source_path'])
            local = Path(item['raw_checkpoint_local_path'])
            sidecar = json.loads((root/item['metadata_path']).read_text())
            raw = json.loads(source.read_text())
            assert local.read_bytes() == source.read_bytes()
            assert not local.resolve().is_relative_to(root.resolve())
            assert not has_permutation_field(sidecar)
            assert sidecar['checkpoint_metadata'] == {k: v for k, v in raw.items() if k != 'row_perm'}
            expected_sweeps = 9 if 'C4-U' in item['key'] else 10
            assert len(sidecar['checkpoint_metadata']['history']) == expected_sweeps
            assert (sidecar['original_post_record'] is None) == ('C4-U' in item['key'])
            checks.append(dict(case_key=item['key'], source_sha256=sha(source),
                               copied_bytes=source.stat().st_size, complete_sweeps=expected_sweeps,
                               terminal_exitcode=sidecar['original_command']['exitcode'],
                               derived_metadata_has_no_permutation=True))
        assert verify(root)['passed']
        # A changed local copy must fail independent ledger verification.
        target = Path(ledger['files'][0]['raw_checkpoint_local_path'])
        good = target.read_bytes(); target.write_bytes(good + b' ')
        try:
            verify(root)
        except AssertionError:
            tamper_rejected = True
        else:
            raise AssertionError('tampered checkpoint copy accepted')
        target.write_bytes(good); assert verify(root)['passed']
        try:
            install(root, 'validation-subset', selected=selected, local_directory=temp/'local-originals')
        except AssertionError:
            overwrite_rejected = True
        else:
            raise AssertionError('existing checkpoint ledger overwritten')
        wrong_root = temp/'wrong-archive-root'; wrong_root.mkdir()
        try:
            install(wrong_root, 'bad-policy', selected=selected, local_directory=wrong_root/'raw-vectors')
        except AssertionError:
            archived_vectors_rejected = True
        else:
            raise AssertionError('full vectors placed inside archive root')
        # A separate fixture tests filtering without adding probes to real work/.
        fixture = temp/'filter-fixture'
        (fixture/'logs').mkdir(parents=True)
        for name in ['stage3-planned-cases.json', 'matrices-and-taus.json']:
            (fixture/'logs'/name).write_bytes((BASE/'logs'/name).read_bytes())
        probe = fixture/'work/post-e/stage3-cora__B0__W16__seed0__tau2/last-completed-sweep.checkpoint.json'
        probe.parent.mkdir(parents=True); probe.write_text('{"row_perm":[0]}')
        found, expected_fixture, excluded = discover(fixture)
        assert not found and len(excluded) == 1 and len(expected_fixture) == 64
        running = temp/'active-command.json'
        running.write_text(json.dumps(dict(status='RUNNING', ended_at=None, method_started_at=1)))
        try:
            terminal_command(running)
        except AssertionError:
            active_job_rejected = True
        else:
            raise AssertionError('active checkpoint accepted for packaging')
    for item in original.values():
        assert sha(item['path']) == item['sha256'], 'original checkpoint modified'
    for name in ['checkpoint_evidence.py', 'build_stage3.py', 'gate_checkpoint_evidence.py']:
        compile((BASE/'scripts'/name).read_text(), name, 'exec')
    implementation = {f'scripts/{name}': sha(BASE/'scripts'/name) for name in
                      ['checkpoint_evidence.py', 'build_stage3.py', 'gate_checkpoint_evidence.py']}
    result = dict(passed=True, at_utc=time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                  scope='packaging validation using two real terminal original checkpoints; no local search/layout/UG recomputation',
                  implementation_sources=implementation, real_checkpoint_checks=checks,
                  complete_expected_post_grid=64, out_of_scope_probe_excluded=True,
                  tamper_rejected=tamper_rejected, ledger_overwrite_rejected=overwrite_rejected,
                  raw_vectors_inside_archive_rejected=archived_vectors_rejected,
                  active_command_rejected=active_job_rejected, original_bytes_unchanged=True,
                  full_checkpoint_campaign_install_pending=True)
    path = BASE/'logs/stage3-checkpoint-evidence-gate.json'
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(passed=True, real_terminal_checkpoints=2, checks=6,
                          raw_source_bytes_unchanged=True, scientific_reruns=False)))


if __name__ == '__main__':
    main()
