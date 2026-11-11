"""Administrative ownership filter; scientific case execution stays in run_stage3.run."""
import argparse, concurrent.futures, hashlib, json, os, platform, sys, time
from pathlib import Path
from run_stage3 import run, BASE

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--assignment', required=True)
    ap.add_argument('--owner', choices=['local', 'remote'], required=True)
    ap.add_argument('--readiness')
    args = ap.parse_args()
    assignment_path = Path(args.assignment).resolve()
    assignment = json.loads(assignment_path.read_text())
    cases = assignment[args.owner + '_cases']
    assert len({r['case_id'] for r in cases}) == len(cases)
    assert not (BASE/'work/split-control/hold-new-admissions.json').exists(), 'Administrative admission hold must be released before the replacement controller starts.'
    host_id = assignment[args.owner + '_host_id']
    readiness = None
    if args.owner == 'remote':
        assert args.readiness, 'Remote host must complete fresh local gates first.'
        readiness_path = Path(args.readiness).resolve()
        readiness = json.loads(readiness_path.read_text())
        assert readiness.get('passed') is True and readiness.get('host_id') == host_id
        assert readiness.get('split_id') == assignment['split_id']
        assert readiness.get('fresh_remote_gates') is True
        assert readiness.get('gate_receipts'), 'A copied local/macOS PASS is not a remote gate.'
        required = {'reference_tables', 'official40', 'candidate_equivalence', 'layout_v7', 'LS_full', 'independent_sorted', 'memory_guard_units'}
        assert required <= {item['category'] for item in readiness['gate_receipts']}
        for item in readiness['gate_receipts']:
            p = BASE/item['path']
            assert digest(p) == item['sha256'], p
    environment = dict(host_id=host_id, platform=platform.platform(), machine=platform.machine(), python=sys.version, pid=os.getpid(), started_at=time.time(), owner=args.owner, split_id=assignment['split_id'], assignment_sha256=digest(assignment_path), scientific_dispatch='unmodified run_stage3.run', workers=2, large_graph_serialized=True, method_limit_seconds=7200, workspace_limit_bytes=8*2**30)
    (BASE/'logs'/f'stage3-{args.owner}-split-controller.json').write_text(json.dumps(environment, ensure_ascii=False, indent=2)+'\n')
    owned = [dict(r, execution_host_id=host_id, split_id=assignment['split_id']) for r in cases]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        records = list(ex.map(run, owned))
    assert all(r['status'] in ['OK', 'INCOMPLETE', 'SKIPPED'] for r in records)
    completion = dict(environment, ended_at=time.time(), cases=len(records), case_ids=[r['case_id'] for r in cases], generation_record_counts={s:sum(r['status']==s for r in records) for s in ['OK','INCOMPLETE','SKIPPED']}, note='Generation/controller statuses are not whole scientific-case PASS. Scientific statuses come from all own/post conditions.')
    (BASE/'logs'/f'stage3-{args.owner}-split-complete.json').write_text(json.dumps(completion, ensure_ascii=False, indent=2)+'\n')
    print('ASSIGNED_CASES_TERMINAL', args.owner, len(records), flush=True)
    if args.owner != 'local':
        return
    # Keep the existing finalizer asleep until the remote bundle was independently
    # imported and verified on this host. No synthetic delegated case records.
    imported_path = BASE/'logs/remote-split-import-verified.json'
    planned = json.loads((BASE/'logs/stage3-planned-cases.json').read_text())
    print('WAITING_FOR_VERIFIED_REMOTE_IMPORT', flush=True)
    while True:
        if imported_path.exists():
            imported = json.loads(imported_path.read_text())
            expected = {r['case_id'] for r in assignment['remote_cases']}
            assert imported.get('passed') is True and imported.get('split_id') == assignment['split_id']
            assert set(imported['case_ids']) == expected
            assert len(imported['canonical_case_records']) == len(expected)
            assert {item['case_id'] for item in imported['canonical_case_records']} == expected
            for item in imported['canonical_case_records']:
                assert item['case_id'] in expected and digest(BASE/item['path']) == item['sha256']
            paths = [BASE/'work/stage3-cases'/r['case_id']/'record.json' for r in planned]
            if all(p.exists() for p in paths):
                all_records = [json.loads(p.read_text()) for p in paths]
                assert all(r['status'] in ['OK','INCOMPLETE','SKIPPED'] for r in all_records)
                marker = BASE/'logs/stage3-run-complete.json'
                assert not marker.exists(), 'Do not overwrite a prior global completion record.'
                marker.write_text(json.dumps(dict(ended=time.time(), cases=len(planned), counts={s:sum(r['status']==s for r in all_records) for s in ['OK','INCOMPLETE','SKIPPED']}, split_id=assignment['split_id'], local_completion=str(BASE/'logs/stage3-local-split-complete.json'), verified_remote_import=str(imported_path), note='All genuine case records are present; final scientific status and archive audits still required.'), indent=2)+'\n')
                print('GLOBAL_CASE_RECORDS_TERMINAL', len(planned), flush=True)
                return
        time.sleep(30)

if __name__ == '__main__':
    main()
