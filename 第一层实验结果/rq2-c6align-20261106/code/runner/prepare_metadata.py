from __future__ import annotations
import hashlib,json,statistics,sys
from pathlib import Path
sys.dont_write_bytecode=True
from campaign import BASE,OUT,acquisition,load_adj,dump,ref,digest

records=[]
for name,entry in acquisition().items():
    if entry.get('protocol_alias_of'):continue
    if entry['status']!='OK':records.append({'matrix':name,'status':'INCOMPLETE','acquisition':entry});continue
    entries=zeros=diagonals=0
    with open(entry['mtx']) as f:
        pattern='pattern' in f.readline().lower();line=f.readline()
        while line.startswith('%'):line=f.readline()
        n,nc,announced=map(int,line.split())
        for line in f:
            fields=line.split()
            if not fields or fields[0].startswith('%'):continue
            entries+=1;diagonals+=int(fields[0])==int(fields[1])
            if not pattern and float(fields[2])==0:zeros+=1
    assert entries==announced
    adj=load_adj(name);degree=[len(row) for row in adj]
    record={'matrix':name,'status':'OK','n':n,'stored_entries':entries,'explicit_zero_entries':zeros,'diagonal_entries':diagonals,
            'nnz_A0':sum(degree),'nnz_A1':sum(degree)+n,'degree_median':statistics.median(degree),'degree_mean':statistics.mean(degree),'degree_max':max(degree),
            'input_mtx_sha256':entry['mtx_sha256'],'source_url':entry['source_url'],'input_path':entry['mtx'],'source_variant':entry.get('source_variant','original'),
            'reference_only':entry.get('reference_only',''),'archive_sha256':entry.get('archive_sha256',''),'archive_member':entry.get('archive_member','derived MTX'),'structure':'stored pattern including explicit zeros','residual_sets':{}}
    for tau in (2,3):
        resid=[v for v,d in enumerate(degree) if d<=tau];record['residual_sets'][str(tau)]={'count':len(resid),'sha256':digest(resid),'fixed_for_both_diag_modes':True}
        dump(OUT/'checks'/f'{name}-residual-tau{tau}.json',{'tau':tau,'original_row_ids':resid,'source':'A0 degree'})
    records.append(record);dump(BASE/'logs/matrix-statistics.json',records);print(name,n,entries,zeros,diagonals,sum(degree),flush=True)
    del adj,degree

