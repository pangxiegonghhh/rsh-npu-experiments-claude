from load import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
d=load(); ok=d[(d.status=='OK')&(d.W==16)]
p=ok[(ok.member=='P-LS')&(ok.d_rule=='D-greedy')&(ok.placement=='tail')].copy()
k=['matrix','start','tau','seed','diag']
a=p.pivot_table(index=k,columns='lambda',values=['sumR','T','sumU','sumGamma'],aggfunc='first')
res=pd.DataFrame({'dR':a[('sumR',1.0)]/a[('sumR',0.0)]-1,'dT':a[('T',1.0)]/a[('T',0.0)]-1,
                  'dR_l05':a[('sumR',0.5)]/a[('sumR',0.0)]-1,'dR_l2':a[('sumR',2.0)]/a[('sumR',0.0)]-1,
                  'dT_l2':a[('T',2.0)]/a[('T',0.0)]-1}).reset_index()
res['pass']=(res.dR<=-0.05)&(res.dR>=-0.15)&(res.dT.abs()<=0.03)
res['R_in']=(res.dR<=-0.05)&(res.dR>=-0.15); res['T_in']=res.dT.abs()<=0.03
print('P-LS(1) vs P-LS(0) cases',len(res),'pass',res['pass'].sum(),'R in range',res.R_in.sum(),'T in range',res.T_in.sum())
A0=res[res.diag=='A0']
print(A0.groupby(['matrix']).agg(n=('dR','size'),dR_min=('dR','min'),dR_med=('dR','median'),dR_max=('dR','max'),dT_min=('dT','min'),dT_med=('dT','median'),dT_max=('dT','max'),npass=('pass','sum')).round(4).to_string())
print(res[res.diag=='A1'].groupby(['matrix']).agg(n=('dR','size'),dR_med=('dR','median'),dT_med=('dT','median'),npass=('pass','sum')).round(4).to_string())
print(A0[A0.seed==0].round(4).to_string())
# seed variance cora/arxiv
s=res[(res.matrix.isin(['cora','ogbn-arxiv']))&(res.diag=='A0')]
print(s.groupby(['matrix','start','tau']).agg(dR_min=('dR','min'),dR_max=('dR','max'),dT_min=('dT','min'),dT_max=('dT','max')).round(4))

# full-row control vs start (after partition, tail, D-greedy)
f=ok[(ok.member=='P-LS-full-control')&(ok.tau.isin(['2','3']))&(ok.placement=='tail')&(ok.d_rule=='D-greedy')]
st=ok[(ok.mv.isin(['C9-Gorder','rsh-α0','rabbit-pilot']))&(ok.tau.isin(['2','3']))&(ok.placement=='tail')&(ok.d_rule=='D-greedy')]
st=st.set_index(['matrix','mv','tau','diag'])
rows=[]
for _,x in f.iterrows():
    s0=st.loc[(x.matrix,x.start,x.tau,x.diag)]
    rows.append(dict(matrix=x.matrix,start=x.start,lam=x['lambda'],tau=x.tau,diag=x.diag,gainR=1-x.sumR/s0.sumR,gainT=1-x['T']/s0['T'],gainU=1-x.sumU/s0.sumU))
fc=pd.DataFrame(rows); fc['pass']=(fc.gainR<=0.02)&(fc.gainT<=0.02)
print('\nfull-row control after partition: cases',len(fc),'pass(gainR<=2% & gainT<=2%)',fc['pass'].sum())
print(fc[fc.diag=='A0'].pivot_table(index=['matrix','start','lam'],columns='tau',values=['gainR','gainT']).round(3).to_string())
# full-row gain (tau none) for reference
fr=ok[(ok.member=='P-LS-full-control')&(ok.tau=='none')&(ok.d_rule=='D-greedy')&(ok.diag=='A0')]
s1=ok[(ok.mv.isin(['C9-Gorder','rsh-α0','rabbit-pilot']))&(ok.tau=='none')&(ok.d_rule=='D-greedy')&(ok.diag=='A0')].set_index(['matrix','mv'])
fr=fr.assign(gR=[1-x.sumR/s1.loc[(x.matrix,x.start)].sumR for _,x in fr.iterrows()],gT=[1-x['T']/s1.loc[(x.matrix,x.start)]['T'] for _,x in fr.iterrows()])
print(fr.pivot_table(index=['matrix','start'],columns='lambda',values=['gR','gT']).round(3).to_string())
