#!/usr/bin/env python3
"""Download the NeutronSparse evaluation matrices into Matrix Market files.

The official SuiteSparse file endpoint is currently intermittently unavailable;
this script therefore keeps the exact paper manifest local and allows the base
URL to be overridden with --base-url.  It downloads each archive once, extracts
one .mtx/.mtx.gz member, and leaves the original archive in --archive-dir for
reproducibility.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import shutil
import ssl
import subprocess
import tarfile
import urllib.request
from pathlib import Path


MANIFEST = Path(__file__).with_name("neutron_dataset_manifest.csv")
SMALL = ["cora", "wiki-RfA", "dawson5", "olafu", "pattern1", "human_gene1"]
SUITE = [
    "wiki-RfA", "dawson5", "olafu", "pattern1", "mip1", "mycielskian15",
    "nd12k", "human_gene1", "F1", "ML_Laplace", "Fault_639", "mouse_gene",
    "audikw_1", "mycielskian17", "mycielskian18", "mycielskian19",
]
ALL = ["cora", "ogbn-arxiv", "reddit", "amazon-product"] + SUITE


def read_manifest() -> dict[str, dict[str, str]]:
    with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def _request(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "rsh-neutron-structure-experiment/1.0"})
    return urllib.request.urlopen(request, timeout=60)


def _copy_response(url: str, target: Path) -> None:
    with _request(url) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle, length=1024 * 1024)


def _safe_extract_matrix(archive: Path, target: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        members = [member for member in tar.getmembers() if member.isfile() and (member.name.endswith(".mtx") or member.name.endswith(".mtx.gz"))]
        if not members:
            raise RuntimeError(f"no Matrix Market file found in {archive}")
        member = sorted(members, key=lambda item: len(item.name))[0]
        stream = tar.extractfile(member)
        if stream is None:
            raise RuntimeError(f"cannot read {member.name} from {archive}")
        if member.name.endswith(".gz"):
            with gzip.GzipFile(fileobj=stream) as decompressed, target.open("wb") as handle:
                shutil.copyfileobj(decompressed, handle, length=1024 * 1024)
        else:
            with stream, target.open("wb") as handle:
                shutil.copyfileobj(stream, handle, length=1024 * 1024)


def _download_one(row: dict[str, str], output_dir: Path, archive_dir: Path, *, dry_run: bool = False) -> dict[str, str]:
    name = row["name"]
    target = output_dir / f"{name}.mtx"
    if target.exists() and target.stat().st_size > 0:
        return {"name": name, "status": "cached", "path": str(target)}
    url = row["download_url"].strip()
    if not url:
        return {"name": name, "status": "missing_url", "matrix_id": row.get("matrix_id", "")}
    if dry_run:
        return {"name": name, "status": "planned", "url": url, "path": str(target)}
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    try:
        if url.endswith(".mtx"):
            _copy_response(url, target)
        else:
            archive = archive_dir / f"{name}.tar.gz"
            if not archive.exists():
                _copy_response(url, archive)
            _safe_extract_matrix(archive, target)
        return {"name": name, "status": "downloaded", "path": str(target), "url": url}
    except Exception as exc:  # keep all matrix attempts visible in the report
        return {
            "name": name,
            "status": "error",
            "url": url,
            "error": repr(exc),
            "fallback": f"ssget -e -i {row.get('matrix_id', '')} -t MM",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch the NeutronSparse matrix manifest.")
    parser.add_argument("--preset", choices=["small", "suite", "all"], default="small")
    parser.add_argument("--name", action="append", dest="names", help="Download one named matrix; repeat this option.")
    parser.add_argument("--output-dir", default="neutron-matrices", help="Directory for extracted .mtx files.")
    parser.add_argument("--archive-dir", default="neutron-archives", help="Directory for downloaded tarballs.")
    parser.add_argument("--base-url", help="Override SuiteSparse base URL, e.g. https://mirror.example/MM")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = read_manifest()
    names = args.names or {"small": SMALL, "suite": SUITE, "all": ALL}[args.preset]
    if args.base_url:
        base = args.base_url.rstrip("/")
        for row in manifest.values():
            if row["source"] == "SuiteSparse" and row["group"]:
                row["download_url"] = f"{base}/{row['group']}/{row['name']}.tar.gz"
    missing = [name for name in names if name not in manifest]
    if missing:
        parser.error(f"unknown matrix names: {', '.join(missing)}")
    output_dir = Path(args.output_dir)
    archive_dir = Path(args.archive_dir)
    results = [_download_one(manifest[name], output_dir, archive_dir, dry_run=args.dry_run) for name in names]
    output_dir.mkdir(parents=True, exist_ok=True)
    report = output_dir / "download_report.json"
    report.write_text(json.dumps({"preset": args.preset, "requested": names, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    for result in results:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if all(result["status"] in {"cached", "downloaded", "planned"} for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
