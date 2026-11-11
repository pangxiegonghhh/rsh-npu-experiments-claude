from __future__ import annotations
import concurrent.futures, datetime, gzip, hashlib, json, shutil, subprocess, tarfile, time, zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REPO = Path("/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t21-rq2-20261106/repo")
DATA = BASE / 'inputs'
DATA.mkdir(exist_ok=True)
SOURCES = {
    'wiki-RfA': ('SNAP', 'wiki-RfA'),
    'dawson5': ('GHS_indef', 'dawson5'),
    'olafu': ('Simon', 'olafu'),
    'pattern1': ('Andrianov', 'pattern1'),
    'human_gene1': ('Belcastro', 'human_gene1'),
}

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest()

def download(name: str, url: str, dest: Path) -> dict:
    entry = {'matrix': name, 'url': url, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    started = time.perf_counter()
    try:
        cmd = ['/usr/bin/curl', '--fail', '--location', '--connect-timeout', '30', '--max-time', '600',
               '--silent', '--show-error', '--output', str(dest), '--write-out', '%{http_code}\n%{url_effective}', url]
        p = subprocess.run(cmd, capture_output=True, text=True)
        entry.update(argv=cmd, returncode=p.returncode, stderr=p.stderr, response_metadata=p.stdout)
        if p.returncode: raise RuntimeError(f'curl exit {p.returncode}: {p.stderr.strip()}')
        entry.update(status='OK', bytes=dest.stat().st_size, sha256=sha(dest))
    except Exception as exc:
        entry.update(status='INCOMPLETE', error=f'{type(exc).__name__}: {exc}')
    entry['download_sec'] = time.perf_counter() - started
    return entry

def suite(name: str, group: str) -> dict:
    dest = DATA / (name + '.tar.gz')
    entry = download(name, f'https://sparse.tamu.edu/MM/{group}/{name}.tar.gz', dest)
    if entry['status'] == 'OK':
        try:
            with tarfile.open(dest, 'r:gz') as archive:
                matches = [m for m in archive.getmembers() if m.isfile() and Path(m.name).name == name + '.mtx']
                assert len(matches) == 1, [m.name for m in matches]
                with archive.extractfile(matches[0]) as source, (DATA / (name + '.mtx')).open('wb') as out:
                    shutil.copyfileobj(source, out)
            entry.update(mtx=str(DATA / (name + '.mtx')), mtx_sha256=sha(DATA / (name + '.mtx')))
        except Exception as exc:
            entry.update(status='INCOMPLETE', error=f'{type(exc).__name__}: {exc}')
    return entry

def arxiv() -> dict:
    dest = DATA / 'arxiv.zip'
    entry = download('ogbn-arxiv', 'https://snap.stanford.edu/ogb/data/nodeproppred/arxiv.zip', dest)
    if entry['status'] == 'OK':
        try:
            with zipfile.ZipFile(dest) as archive:
                edges = [x for x in archive.namelist() if x.endswith('/raw/edge.csv.gz')]
                nodes = [x for x in archive.namelist() if x.endswith('/raw/num-node-list.csv.gz')]
                assert len(edges) == len(nodes) == 1
                with archive.open(nodes[0]) as stream: n = int(gzip.decompress(stream.read()).decode().strip())
                path = DATA / 'ogbn-arxiv.mtx'
                with archive.open(edges[0]) as compressed, gzip.open(compressed, 'rt') as source, path.open('w') as out:
                    out.write('%%MatrixMarket matrix coordinate pattern general\n')
                    out.write('% Original directed OGB arxiv edges; A0/A1 preprocessing is separate.\n')
                    out.write(f'{n} {n} 1166243\n')
                    count = 0
                    for line in source:
                        a, c = map(int, line.strip().split(',')); out.write(f'{a+1} {c+1}\n'); count += 1
                assert count == 1166243 and n == 169343, (n, count)
            entry.update(mtx=str(path), mtx_sha256=sha(path), n=n, original_directed_edges=count,
                         conversion='All original directed edges, no diagonal/symmetry changes during conversion.')
        except Exception as exc:
            entry.update(status='INCOMPLETE', error=f'{type(exc).__name__}: {exc}')
    return entry

if __name__ == '__main__':
    assert json.loads((BASE / 'logs/selfcheck-gate.json').read_text())['passed']
    cora = REPO / '第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx'
    entries = [{'matrix': 'cora', 'status': 'OK', 'mtx': str(cora), 'mtx_sha256': sha(cora), 'source': 'exact repository file'}]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(suite, name, group) for name, (group, _) in SOURCES.items()] + [pool.submit(arxiv)]
        for job in concurrent.futures.as_completed(jobs):
            entry = job.result(); entries.append(entry)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
            (BASE / 'logs/input-acquisition.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2))
