#!/usr/bin/env python3
"""Commit and push one experiment's complete, already-reviewed workspace."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True, check=check)


def inspect_files() -> tuple[list[str], dict[str, int]]:
    result = git('ls-files', '-z', '--cached', '--others', '--exclude-standard').stdout
    names = sorted(set(filter(None, result.split('\0'))))
    patterns = [re.compile(rb'gh[pousr]_[A-Za-z0-9]{25,}'),
                re.compile(rb'github_pat_[A-Za-z0-9_]{25,}'),
                re.compile(rb'AKIA[A-Z0-9]{16}')]
    markers = [b'-----BEGIN ' + kind + b' PRIVATE KEY-----'
               for kind in (b'OPENSSH', b'RSA', b'EC', b'DSA')]
    problems: list[str] = []
    sizes: dict[str, int] = {}
    for name in names:
        path = ROOT / name
        if path.is_symlink():
            problems.append(f'symlink needs explicit review: {name}')
            continue
        if not path.is_file():
            continue  # A staged deletion is permitted.
        if '.private' in path.relative_to(ROOT).parts or path.name.startswith('.env') and path.name != '.env.example':
            problems.append(f'credential path: {name}')
        size = path.stat().st_size
        sizes[name] = size
        if size >= 100 * 1024 * 1024:
            problems.append(f'100MiB limit requires LFS/Release: {name}')
            continue
        data = path.read_bytes()
        if any(marker in data for marker in markers) or any(p.search(data) for p in patterns):
            problems.append(f'possible secret (value omitted): {name}')
    if problems:
        raise ValueError('\n'.join(problems))
    return names, sizes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--outcome', choices=['pass', 'fail', 'incomplete'], required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    for label in (args.experiment, args.run_id):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', label):
            raise ValueError('experiment/run-id must be a simple label')
    run = (ROOT / args.run_dir).resolve()
    run.relative_to(ROOT)  # Reject a path outside the workspace.
    for required in (run / 'summary.md', ROOT / 'docs/e0-e6-experiments/resume.md',
                     ROOT / 'docs/e0-e6-experiments/experiment-status.md'):
        if not required.is_file():
            raise ValueError(f'missing required record: {required}')
    branch = git('branch', '--show-current').stdout.strip()
    if not branch:
        raise ValueError('detached HEAD: choose a branch before publishing')
    names, sizes = inspect_files()
    overview = {'dry_run': args.dry_run, 'branch': branch,
                'experiment': args.experiment, 'run_id': args.run_id, 'outcome': args.outcome,
                'files': len(names), 'bytes': sum(sizes.values()),
                'top_level_file_counts': dict(Counter(Path(n).parts[0] for n in names)),
                'note': 'All non-ignored workspace changes are included; review docs and evidence before publishing.'}
    print(json.dumps(overview, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        return
    origin = git('remote', 'get-url', 'origin').stdout.strip()
    head = git('rev-parse', 'HEAD').stdout.strip()
    remote = git('ls-remote', '--exit-code', 'origin', f'refs/heads/{branch}', check=False)
    if remote.returncode not in (0, 2):
        raise RuntimeError('Cannot read remote branch: ' + remote.stderr.strip())
    if remote.returncode == 0:
        git('fetch', 'origin', f'refs/heads/{branch}')
        if git('merge-base', '--is-ancestor', 'FETCH_HEAD', 'HEAD', check=False).returncode != 0:
            raise ValueError('Remote branch has unintegrated commits; inspect and resolve before retrying. No force push.')
    intent = {'experiment': args.experiment, 'run_id': args.run_id, 'outcome': args.outcome,
              'workspace_head_before_publication': head,
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'workspace snapshot; outcome is supplied by the reviewed run summary'}
    (run / 'github-publish-intent.json').write_text(json.dumps(intent, ensure_ascii=False, indent=2) + '\n')
    git('add', '--all')
    changes = git('diff', '--cached', '--quiet', check=False)
    if changes.returncode not in (0, 1):
        raise RuntimeError('Could not inspect staged changes')
    if changes.returncode == 1:
        git('commit', '-m', f'chore(experiments): archive {args.experiment} {args.run_id} ({args.outcome})')
    git('push', '--set-upstream', 'origin', 'HEAD')
    local_sha = git('rev-parse', 'HEAD').stdout.strip()
    pushed = git('ls-remote', 'origin', f'refs/heads/{branch}').stdout.split()
    if not pushed or pushed[0] != local_sha:
        raise RuntimeError('Remote SHA does not match HEAD; do not report upload complete')
    receipt = {**intent, 'remote': origin, 'branch': branch, 'commit': local_sha,
               'remote_sha_verified': True}
    private = ROOT / '.private'
    private.mkdir(exist_ok=True)
    (private / 'last-push.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr.strip(), file=sys.stderr)
        else:
            print(str(error), file=sys.stderr)
        sys.exit(1)
