"""Create genuine readable M8 timing tables as a PDF, preserving numeric CSV strings."""
from pathlib import Path
import csv,hashlib,json,zlib
p=Path(__file__).resolve().parent
data=list(csv.DictReader((p/'timing-observations.csv').open()))
assert len(data)==16800
names=sorted(set(q['case'] for q in data));records=[]
fields=[q for q in data[0] if q!='case']
records.append('COLUMNS|'+','.join(fields))
for name in names:
    records.append('CASE|'+name)
    rows=sorted([q for q in data if q['case']==name],key=lambda q:int(q['block']));assert len(rows)==20
    for row in rows:records.append('T|'+','.join(row[k] for k in fields))
canonical='\n'.join(records)+'\n';h=hashlib.sha256(canonical.encode('ascii')).hexdigest();(p/'timing-data-records.txt').write_bytes(canonical.encode('ascii'))
header=['M8 direct gather vs AIV pack: complete accepted timing observations',
        '840 configurations x 20 randomized blocks. Ascend 910B2 physical NPU 5 / CANN 9.0.0.',
        'T rows preserve the original numeric strings and units (us). Block order is 0..19.',
        'us: device timed-section makespan. event_us: whole ACL kernel event time.',
        'us_per_window: makespan divided by all windows across 24 cores, not single-core latency.',
        'reader_us_sum / pack_us_sum: accumulated stage durations across cores, not MTE2 busy.',
        'Pack uses one GM slot per group and READY/ACK. No across-window producer-consumer overlap.',
        'Every case passed identity-consumer readback before timing. Correctness outputs are separate.',
        'DATA_RECORDS_SHA256 '+h,'']
footer=['','Source evidence SHA256:']
for path in [p/'timing-observations.csv',p/'manifest.json',p/'kernel.cpp',p/'host.cpp',p/'registration.md',p/'analysis.json',p/'input-audit.json',p/'environment/p0-accepted.json',p/'environment/resume.txt',p/'environment/cann-install.txt']:
    footer.append('FILEHASH|'+str(path.relative_to(p))+'|'+hashlib.sha256(path.read_bytes()).hexdigest())
evidence=[]
for name in ['environment/resume.txt','environment/cann-install.txt','environment/p0-accepted.json','input-audit.json','calibration-final-quality.json','batch-multipliers.txt','batch-calibration.json','formal-source-hashes.json']:
    file=p/name;evidence.append('EVIDENCEFILE|'+name)
    for line in file.read_text().splitlines():
        assert line.isascii(),name
        evidence.append('E|'+line)
    evidence.append('END_EVIDENCEFILE')
for journal in sorted((p/'blocks').glob('b*-accepted.json')):
    evidence.append('EVIDENCEFILE|'+str(journal.relative_to(p)))
    evidence.extend('E|'+line for line in journal.read_text().splitlines());evidence.append('END_EVIDENCEFILE')
for stage in ['results-first','results-stress','results-check','results-v3-stress']:
    for gate in sorted((p/stage).glob('*/gate.json')):
        evidence.append('CHECK|'+stage+'|'+gate.parent.name+'|'+json.dumps(json.loads(gate.read_text()),separators=(',',':')))
lines=header+records+footer+['','Environment, calibration, acceptance journals and correctness checks:']+evidence
assert max(map(len,lines))<=250
objects=[None,None,None]
def obj(v):objects.append(v);return len(objects)-1
font=obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>');pages=[];per_page=70
for start in range(0,len(lines),per_page):
    cmd=['BT /F1 7 Tf 10.5 TL 40 790 Td']
    for i,line in enumerate(lines[start:start+per_page]):
        escaped=line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        if i:cmd.append('T*')
        cmd.append('('+escaped+') Tj')
    cmd.extend(['ET','BT /F1 7 Tf 40 30 Td (Page '+str(start//per_page+1)+') Tj ET'])
    stream=zlib.compress(('\n'.join(cmd)+'\n').encode('ascii'))
    contents=obj(b'<< /Length '+str(len(stream)).encode()+b' /Filter /FlateDecode >>\nstream\n'+stream+b'\nendstream')
    page=obj(('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1191 842] /Resources << /Font << /F1 '+str(font)+' 0 R >> >> /Contents '+str(contents)+' 0 R >>').encode());pages.append(page)
objects[1]=b'<< /Type /Catalog /Pages 2 0 R >>';objects[2]=('<< /Type /Pages /Count '+str(len(pages))+' /Kids ['+' '.join(str(q)+' 0 R' for q in pages)+'] >>').encode()
output=bytearray(b'%PDF-1.4\n% readable M8 data tables\n');offsets=[0]
for i,value in enumerate(objects[1:],1):offsets.append(len(output));output.extend(str(i).encode()+b' 0 obj\n'+value+b'\nendobj\n')
xref=len(output);output.extend(('xref\n0 '+str(len(objects))+'\n0000000000 65535 f \n').encode())
for offset in offsets[1:]:output.extend(f'{offset:010d} 00000 n \n'.encode())
output.extend(('trailer\n<< /Size '+str(len(objects))+' /Root 1 0 R >>\nstartxref\n'+str(xref)+'\n%%EOF\n').encode())
file=p.parent/'M8-complete-timing-tables-20261115.pdf';file.write_bytes(output)
print(json.dumps(dict(records_sha256=h,pdf_bytes=len(output),pages=len(pages),cases=len(names),observations=len(data))))
