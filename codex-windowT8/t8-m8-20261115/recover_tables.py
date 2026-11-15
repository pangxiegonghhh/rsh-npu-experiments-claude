"""Recover original numeric timing strings from the genuine readable evidence PDF."""
from pathlib import Path
import argparse,csv,hashlib,io,json,re,shutil
from pypdf import PdfReader

def main():
    parser=argparse.ArgumentParser();parser.add_argument('pdf');parser.add_argument('--out',default=str(Path(__file__).resolve().parent.parent/'t8-m8-results-20261115'));args=parser.parse_args()
    source=Path(args.pdf);out=Path(args.out);out.mkdir(exist_ok=True);code=Path(__file__).resolve().parent
    reader=PdfReader(source);lines=[line for page in reader.pages for line in page.extract_text().splitlines()]
    expected=next(line.split(' ',1)[1] for line in lines if line.startswith('DATA_RECORDS_SHA256 '));records=[];data=[];fields=None;name=None;hashes={};evidence={};active=None;checks=[]
    for line in lines:
        if line.startswith('COLUMNS|'):fields=line.split('|',1)[1].split(',');records.append(line)
        elif line.startswith('CASE|'):name=line.split('|',1)[1];records.append(line)
        elif line.startswith('T|'):
            assert fields and name;v=line.split('|',1)[1].split(',');assert len(v)==len(fields);data.append(dict(case=name,**dict(zip(fields,v))));records.append(line)
        elif line.startswith('FILEHASH|'):
            _,file,h=line.split('|');hashes[file]=h
        elif line.startswith('EVIDENCEFILE|'):active=line.split('|',1)[1];assert active not in evidence;evidence[active]=[]
        elif line=='END_EVIDENCEFILE':active=None
        elif line.startswith('E|'):
            assert active;evidence[active].append(line[2:])
        elif line.startswith('CHECK|'):
            _,stage,case,body=line.split('|',3);gate=json.loads(body);assert gate['status']=='PASS' and gate['all_tiles'];checks.append((stage,case,gate))
    canonical=(chr(10).join(records)+chr(10)).encode('ascii');actual=hashlib.sha256(canonical).hexdigest();assert actual==expected,(actual,expected)
    assert len(data)==16800 and len({(r['case'],r['block']) for r in data})==16800
    assert len({r['case'] for r in data})==840 and {int(r['block']) for r in data}==set(range(20))
    assert min(float(r['us']) for r in data)>=1000
    counts={stage:sum(q[0]==stage for q in checks) for stage in {q[0] for q in checks}}
    assert counts=={'results-first':48,'results-stress':48,'results-check':840,'results-v3-stress':48},counts
    (out/'timing-data-records.txt').write_bytes(canonical)
    buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=['case']+fields);writer.writeheader();writer.writerows(sorted(data,key=lambda x:(x['case'],int(x['block']))));raw=buf.getvalue().encode('ascii')
    assert hashlib.sha256(raw).hexdigest()==hashes['timing-observations.csv'];(out/'timing-observations.csv').write_bytes(raw)
    verified=[]
    for file,h in hashes.items():
        if file in ['timing-observations.csv','analysis.json']:continue
        if file in evidence:
            text=chr(10).join(evidence[file]);text+=chr(10) if Path(file).suffix=='.txt' else ''
            b=text.encode('utf-8');assert hashlib.sha256(b).hexdigest()==h,(file,'PDF evidence text hash')
        else:
            local=code/file;assert local.exists(),file;b=local.read_bytes()
            if hashlib.sha256(b).hexdigest()!=h:b=local.read_text(encoding='utf-8').encode('utf-8')
            assert hashlib.sha256(b).hexdigest()==h,(file,'local source hash')
        dest=out/'provenance'/file;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b);verified.append(file)
    for file,content in evidence.items():
        if file in hashes:continue
        dest=out/'provenance'/file;dest.parent.mkdir(parents=True,exist_ok=True)
        text=chr(10).join(content)+(chr(10) if Path(file).suffix=='.txt' else '');dest.write_bytes(text.encode('utf-8'))
    for stage,case,gate in checks:
        dest=out/'provenance'/stage/case/'gate.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(gate,indent=2),encoding='utf-8')
    shutil.copyfile(out/'provenance/manifest.json',out/'manifest.json')
    # Derived accepted-block tables, explicitly separated from the remote trial directories.
    # Original acceptance journals and remote paths remain under provenance/blocks.
    blocks=out/'blocks';blocks.mkdir(exist_ok=True)
    for block in range(20):
        dest=blocks/f'recovered-b{block:02d}';dest.mkdir(exist_ok=True)
        with (dest/'timing.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['case']+fields);w.writeheader();w.writerows(r for r in data if int(r['block'])==block)
        journal=json.loads((out/'provenance/blocks'/f'b{block:02d}-accepted.json').read_text(encoding='utf-8'))
        for group in journal['groups']:group['path']=str(dest.relative_to(out)).replace('\\','/')
        (blocks/f'b{block:02d}-accepted.json').write_text(json.dumps(journal,indent=2),encoding='utf-8')
    result=dict(status='PASS',cases=840,observations=16800,blocks=20,pdf_pages=len(reader.pages),records_sha256=actual,original_csv_sha256=hashes['timing-observations.csv'],verified_source_files=verified,correctness_gates=counts,remote_analysis_sha256=hashes['analysis.json'],source_files_sha256=hashes,scope='All accepted timing strings, metadata and readable correctness gates; device per-core binary stats and readback vectors remain in the remote full archive.')
    (out/'recovery-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');shutil.copyfile(source,out/'source-timing-tables.pdf');shutil.copyfile(code/'analyze.py',out/'analyze.py')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
