"""Verify protocol condition coverage and file references before final packaging."""
from __future__ import annotations
import collections,csv,json,re
from pathlib import Path

def verify(out:Path,base:Path,expected:list[dict])->dict:
    from finalize import condition_key,missing_rows,MATRICES
    def read(name:str)->list[dict]:
        with (out/name).open(newline='') as f:rows=list(csv.DictReader(f))
        for row in rows:
            if row.get('W'):row['W']=int(row['W'])
            if row.get('tau') and row['tau']!='none':row['tau']=int(row['tau'])
        return rows
    rows=read('results.csv');joint=read('joint.csv');expected_rows=[];expected_joint=[]
    for spec in expected:
        rr,jj=missing_rows(spec,'EXPECTED','')
        expected_rows.extend(rr);expected_joint.extend(jj)
    main=[r for r in rows if r['member'] not in ('B-RSH-ref','B-Neutron-ref')]
    def index(data:list[dict])->dict:
        result={condition_key(r):r for r in data}
        assert len(result)==len(data),'Duplicate result conditions'
        return result
    actual=index(main);wanted=index(expected_rows);actual_joint=index(joint);wanted_joint=index(expected_joint)
    assert actual.keys()==wanted.keys(),{'missing':list(wanted.keys()-actual.keys())[:10],'extra':list(actual.keys()-wanted.keys())[:10]}
    assert actual_joint.keys()==wanted_joint.keys(),'Joint condition coverage mismatch'
    referenced=set()
    for row in rows:
        assert row['status'] in ('OK','SKIPPED','INCOMPLETE')
        if row['status']!='OK':assert row['note'];continue
        for field in ('n','k_windows','sumU','T','sumGamma','sumR','R_p50','R_p90','R_max','sumR_minus_Gamma'):int(row[field])
        match=re.search(r'order=([^;]+)',row['note']);assert match,row
        path=out/match.group(1);assert path.is_file(),path;referenced.add(match.group(1))
    for key,row in actual_joint.items():
        peer=actual[key]
        assert all(row[field]==peer[field] for field in ('status','sumU','T','sumGamma','sumR')),(key,row,peer)
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['commit']=='87594cc9e80e800c77a65988c09f7067b63957be'
    assert manifest['tree']=='f8025fa031f1a56906de58e21ec730f6b6666293'
    assert manifest['selfcheck']['first_line']=='Table A self-check: OK' and manifest['selfcheck']['returncode']==0
    assert manifest['CPU_only'] and not manifest['pushed'] and manifest['repository_unchanged']
    stats={x['matrix']:x for x in manifest['matrices']};assert set(stats)==set(MATRICES),set(stats)
    for name,item in stats.items():
        assert item['source_url'] and re.fullmatch(r'[0-9a-f]{64}',item['input_mtx_sha256'])
        assert item['explicit_zero_entries']==(11493 if name=='wiki-RfA' else 0)
    independent=json.loads((base/'logs/independent-campaign-audit.json').read_text());assert independent['passed']
    assert {x['matrix']for x in independent['raw_input_preprocessing']}==set(MATRICES)
    for item in independent['raw_input_preprocessing']:
        assert all(item[k]==stats[item['matrix']][k] for k in ('n','nnz_A0','nnz_A1')),item
    return {'passed':True,'expected_specs':len(expected),'required_result_conditions':len(main),'joint_conditions':len(joint),
            'total_result_rows':len(rows),'referenced_order_files':len(referenced),'result_status_counts':dict(collections.Counter(r['status']for r in rows)),
            'joint_status_counts':dict(collections.Counter(r['status']for r in joint)),
            'exact_condition_coverage':True,'all_OK_rows_have_order_files':True,'joint_matches_results':True,
            'independent_audit_permutations_checked':independent['permutations_checked']}
