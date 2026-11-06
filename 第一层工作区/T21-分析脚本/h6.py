from load import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
d=load(); ok=d[(d.status=='OK')&(d.W==16)&(d.member.isin(['C6','C6-M']))]
ok=ok.assign(mnc=ok.mnc.fillna(0))
rows=[]
for (m,dg,tau,pl,rule),g in ok.groupby(['matrix','diag','tau','placement','d_rule']):
    g=g.set_index('mnc')
    if 0 not in g.index: continue
    for mnc in (1,4,16):
        if mnc not in g.index: continue
        rows.append(dict(matrix=m,diag=dg,tau=tau,pl=pl,rule=rule,mnc=mnc,dGamma=g.loc[mnc,'sumGamma']/g.loc[0,'sumGamma']-1,dU=g.loc[mnc,'sumU']/g.loc[0,'sumU']-1,
          dT=g.loc[mnc,'T']/g.loc[0,'T']-1,dR=g.loc[mnc,'sumR']/g.loc[0,'sumR']-1,dtime=g.loc[mnc,'order_sec']/g.loc[0,'order_sec']-1))
h=pd.DataFrame(rows)
main=h[(h.mnc==4)&(h.rule=='D-greedy')&(h.pl.isin(['none','tail']))]
main=main.assign(pass_=(main.dGamma<0)&(main.dU<=0.05))
print('mnc=4 cases',len(main),'pass',main.pass_.sum())
print(main[main.diag=='A0'].round(4).to_string())
print(h[(h.diag=='A0')&(h.tau=='none')&(h.rule=='D-greedy')].round(4).to_string())
# partition time
t=ok[(ok.diag=='A0')&(ok.tau=='none')&(ok.d_rule=='own')][['matrix','mnc','order_sec']].pivot(index='matrix',columns='mnc',values='order_sec')
print(t.round(1)); print((t.div(t[0.0],axis=0)-1).round(3))
