"""Produce a derived T23 results copy with case-level host provenance.

Original science tables remain unchanged. Assignment alone is not proof that
any condition executed, and inherited Rabbit coarse timing may be from a
different host than the recorded case host.
"""
import argparse
import csv
import hashlib
import json
from itertools import zip_longest
from pathlib import Path
from split_host_ledger import BASE, ledger

def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--final',action='store_true')
    args=parser.parse_args();src=args.input.resolve();dst=args.output.resolve()
    assert src.is_file() and not dst.exists() and src!=dst
    assert not dst.is_relative_to((BASE/'repo').resolve())
    assert not dst.is_relative_to((BASE/'delivery').resolve()), 'write and validate in staging first'
    before=sha(src);case_rows=ledger(final=args.final)
    index={(x['matrix'],x['method'],str(x['W']),str(x['seed'])):x for x in case_rows}
    assert len(index)==409
    added=['case_id','split_owner','recorded_execution_host_id','host_provenance_note']
    dst.parent.mkdir(parents=True,exist_ok=True)
    count=0
    with src.open(newline='') as inp,dst.open('x',newline='') as out:
        reader=csv.DictReader(inp);original=reader.fieldnames
        assert original and not set(added).intersection(original)
        writer=csv.DictWriter(out,fieldnames=original+added);writer.writeheader()
        for row in reader:
            key=(row['matrix'],row['member'],row['W'],row['seed'])
            case=index[key]
            row.update(case_id=case['case_id'],split_owner=case['split_owner'],
                       recorded_execution_host_id=case['recorded_execution_host_id'],
                       host_provenance_note=case['provenance_note'])
            writer.writerow(row);count+=1
    assert sha(src)==before
    # Verify exact original field values and order, not just aggregate counts.
    with src.open(newline='') as a,dst.open(newline='') as b:
        ar=csv.DictReader(a);br=csv.DictReader(b)
        i=0
        for i,(old,new) in enumerate(zip_longest(ar,br),1):
            assert old is not None and new is not None, 'row count changed'
            assert all(old[k]==new[k] for k in original),i
        assert i==count
    print(json.dumps(dict(rows=count,input_sha256=before,output_sha256=sha(dst),final=args.final,
                          note='Derived copy; raw values preserved. Split owner is not execution proof; historical coarse timing may be from another host.')))

if __name__=='__main__':main()
