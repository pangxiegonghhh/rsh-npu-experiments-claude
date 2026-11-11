"""Create an explicit, non-destructive case/host evidence ledger for T23.

The ledger describes assignment and recorded host provenance. It does not
assert that all scientific conditions succeeded or import remote evidence.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ASSIGNMENT = BASE/'handoff/T23-split-20261109/assignment.json'
PLANNED = BASE/'logs/stage3-planned-cases.json'
REMOTE_PROOF = BASE/'logs/remote-split-import-verified.json'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def ledger(final=False):
    assignment, planned = read(ASSIGNMENT), read(PLANNED)
    assert digest(PLANNED)==assignment['planned_catalog_sha256']
    assert len(planned)==409 and len({x['case_id'] for x in planned})==409
    local={x['case_id'] for x in assignment['local_cases']}
    remote={x['case_id'] for x in assignment['remote_cases']}
    assert len(local)==21 and len(remote)==20 and not local.intersection(remote)
    assert local|remote <= {x['case_id'] for x in planned}
    if final:
        proof=read(REMOTE_PROOF)
        assert proof.get('passed') is True and proof.get('split_id')==assignment['split_id']
        assert set(proof['case_ids'])==remote
        entries=proof['canonical_case_records']
        assert len(entries)==20 and {x['case_id'] for x in entries}==remote
        for item in entries:
            path=(BASE/item['path']).resolve()
            expected=(BASE/'work/stage3-cases'/item['case_id']/'record.json').resolve()
            assert path==expected and path.is_relative_to(BASE.resolve()) and digest(path)==item['sha256']
    rows=[]
    for case in planned:
        key=case['case_id']; p=BASE/'work/stage3-cases'/key/'record.json'
        record=read(p) if p.exists() else None
        owner=(assignment['local_host_id'] if key in local else
               assignment['remote_host_id'] if key in remote else 'completed_before_split')
        actual=record.get('execution_host_id','') if record else ''
        if key in local|remote and actual:
            assert actual==owner, (key,actual,owner)
        if final: assert record is not None, key
        if final and key in remote:
            assert actual==owner, ('remote host provenance missing or mismatched',key,actual)
        rows.append(dict(case_id=key,matrix=case['matrix'],method=case['method'],W=case['W'],seed=case['seed'],
                         split_owner=owner,case_record_exists=bool(record),
                         case_record_sha256=digest(p) if record else '',recorded_execution_host_id=actual,
                         generation_record_status=record.get('status','') if record else '',
                         provenance_note=('Host is explicitly recorded in case metadata; condition execution still depends on raw stage records.' if actual else
                                          'No execution host is recorded in this case record; split owner is assignment only, not proof of execution.')))
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--final',action='store_true');args=parser.parse_args()
    rows=ledger(args.final);out=args.output.resolve();assert not out.exists()
    assert not out.is_relative_to((BASE/'repo').resolve())
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(rows=len(rows),output=str(out),sha256=digest(out),final=args.final,
                          source_assignment_sha256=digest(ASSIGNMENT),
                          limitation='Assignment is not proof that a condition executed; inherited Rabbit coarse timing may originate on another host.')))

if __name__=='__main__':main()
