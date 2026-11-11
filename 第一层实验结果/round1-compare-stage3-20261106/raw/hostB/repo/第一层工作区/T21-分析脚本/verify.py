# Independent recomputation of T21 headline counts: csv module only, no pandas / scipy.
import csv, collections, math, sys
from pathlib import Path
B=str(Path(__file__).resolve().parents[2]/'第一层实验结果'/'rq2-validate-20261106')+'/'
def rows(f): return list(csv.DictReader(open(B+f,encoding='utf-8')))
R=[x for x in rows('results.csv') if x['member'] not in ('P-LS','P-LS-full-control','C6','C6-M')]
J=rows('joint.csv')
import os
S=str(Path(__file__).resolve().parents[2]/'第一层实验结果'/'rq2-c6align-20261106')+'/'
if os.path.exists(S+'joint-c6align.csv') and not os.environ.get('RQ2_NO_SUPPLEMENT'):
    J=[x for x in J if not (x['matrix']=='pattern1' and x['member'] in ('C6','C6-M'))]+list(csv.DictReader(open(S+'joint-c6align.csv',encoding='utf-8')))
    print('[verify] pattern1 C6 / C6-M taken from rq2-c6align-20261106')
def var(x):
    m=x['member']
    if m=='C6-M': return 'C6-M(mnc=%d)'%int(float(x['mnc']))
    if m.startswith('P-LS'): return '%s[%s,%g,%d]'%(m,x['start'],float(x['lambda']),int(float(x['seed'])))
    return m
D=[dict(x,v=var(x)) for x in R+J if x['status']=='OK']
f=lambda x,k: float(x[k])
idx={}
for x in D: idx[(x['matrix'],x['v'],x['diag'],float(x['W']),x['tau'],x['placement'],x['d_rule'])]=x
BASE=['B0','rsh-α0','rabbit-pilot','neutron-pilot','C9-Gorder','C9-S','C10-BP','B-RCM-ref','SlashBurn','C6','C6-M(mnc=4)']
# H1
cases=set((k[0],k[1],k[2]) for k in idx if k[3]==16 and k[4]=='none' and k[6]=='D-greedy')
p=0
for m,v,dg in cases:
    x=idx.get((m,v,dg,16.0,'none','none','D-exact')) or idx[(m,v,dg,16.0,'none','none','D-greedy')]
    p+= (f(x,'sumR')-f(x,'sumGamma'))/f(x,'k_windows')<=1.5
print('H1 pass',p,'of',len(cases))
# H2
n=n10=ne=n80=0
for k,x in idx.items():
    if k[3]!=16 or k[6]!='own' or k[5] not in ('none','tail'): continue
    g=idx.get(k[:6]+('D-greedy',));
    if not g: continue
    n+=1; red=1-f(g,'sumR')/f(x,'sumR'); n10+=red>=0.10
    e=idx.get(k[:6]+('D-exact',))
    if e: ne+=1; n80+=(f(x,'sumR')-f(g,'sumR'))/(f(x,'sumR')-f(e,'sumR'))>=0.8
print('H2 red>=10%',n10,'of',n,' cap>=80%',n80,'of',ne)
# H3 spearman (average ranks)
def rank(a):
    s=sorted(range(len(a)),key=lambda i:a[i]); r=[0]*len(a); i=0
    while i<len(s):
        j=i
        while j+1<len(s) and a[s[j+1]]==a[s[i]]: j+=1
        for t in range(i,j+1): r[s[t]]=(i+j)/2+1
        i=j+1
    return r
def pearson(a,b):
    ma,mb=sum(a)/len(a),sum(b)/len(b); c=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    return c/math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
for m in ['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']:
    xs=[idx[(m,v,'A0',16.0,'none','none','own')] for v in BASE if (m,v,'A0',16.0,'none','none','own') in idx]
    print('H3',m,len(xs),round(pearson(rank([f(x,'meanU') for x in xs]),rank([f(x,'meanGamma') for x in xs])),3))
# H4
for m in ['cora','ogbn-arxiv']:
    for dg in ['A0','A1']:
        a=idx[(m,'C9-S',dg,16.0,'none','none','own')]; b=idx[(m,'C9-Gorder',dg,16.0,'none','none','own')]
        print('H4',m,dg,'dGamma %.4f dT %.4f'%(f(b,'sumGamma')/f(a,'sumGamma')-1,f(b,'T')/f(a,'T')-1))
# H5
pl=[x for x in D if x['member']=='P-LS' and x['d_rule']=='D-greedy' and x['placement']=='tail']
g=collections.defaultdict(dict)
for x in pl: g[(x['matrix'],x['start'],x['tau'],x['seed'],x['diag'])][float(x['lambda'])]=x
ok=0
for k,d in g.items():
    dR=f(d[1.0],'sumR')/f(d[0.0],'sumR')-1; dT=f(d[1.0],'T')/f(d[0.0],'T')-1
    ok+= -0.15<=dR<=-0.05 and abs(dT)<=0.03
print('H5a pass',ok,'of',len(g))
fc=[x for x in D if x['member']=='P-LS-full-control' and x['tau'] in ('2','3') and x['placement']=='tail' and x['d_rule']=='D-greedy']
ok=0
for x in fc:
    s=idx[(x['matrix'],x['start'],x['diag'],16.0,x['tau'],'tail','D-greedy')]
    ok+= (1-f(x,'sumR')/f(s,'sumR'))<=0.02 and (1-f(x,'T')/f(s,'T'))<=0.02
print('H5b pass',ok,'of',len(fc))
# H6
ok=n=0
for k,x in idx.items():
    if k[1]!='C6-M(mnc=4)' or k[6]!='D-greedy' or k[5] not in ('none','tail'): continue
    c=idx[(k[0],'C6')+k[2:]]; n+=1
    ok+= f(x,'sumGamma')<f(c,'sumGamma') and f(x,'sumU')/f(c,'sumU')-1<=0.05
print('H6 pass',ok,'of',n)
# H7
n=nu=0
for k,x in idx.items():
    if k[2]!='A0' or k[3]!=16 or k[4]!='none' or k[6]!='own': continue
    y=idx.get(k[:2]+('A1',)+k[3:])
    if not y: continue
    n+=1; du=f(y,'meanU')/f(x,'meanU')-1; nu+=0.10<=du<=0.25
print('H7 U in range',nu,'of',n)
for m in ['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']:
    for tau in ['none','2','3']:
        pl='none' if tau=='none' else 'tail'
        best={}
        for dg in ['A0','A1']:
            c=[(f(idx[(m,v,dg,16.0,tau,pl,'own')],'T'),v) for v in BASE if (m,v,dg,16.0,tau,pl,'own') in idx]
            mn=min(c)[0]; best[dg]=sorted(v for t,v in c if t==mn)
        if best['A0']!=best['A1']: print('H7 first place changes',m,tau,best)
# H8
mono=collections.Counter()
for m in ['cora','dawson5','wiki-RfA']:
    for v in ['B0','rsh-α0','C9-Gorder','C10-BP']:
        for dg in ['A0','A1']:
            r=[f(idx[(m,v,dg,W,'none','none','indep-CBM')],'sumR')/f(idx[(m,v,dg,W,'none','none','D-greedy')],'sumR') for W in (16.,32.,64.,128.)]
            mono[dg]+= all(b<a for a,b in zip(r,r[1:]))
print('H8 monotone decreasing',dict(mono),'of 12 each')
