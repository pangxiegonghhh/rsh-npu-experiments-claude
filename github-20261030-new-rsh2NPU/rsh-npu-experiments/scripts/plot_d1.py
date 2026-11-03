"""Offline D1 figure from saved process-level analysis, no device work."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d1'
def main():
    data=json.loads((D/'local_audit.json').read_text());rows=data['rows'];names=['ns3Da / 16','email-Enron / 64','ca-HepTh / 256','web-NotreDame / 16','thermal1 / 64']
    fig,axes=plt.subplots(1,2,figsize=(12,4.4),layout='constrained');a=axes[0];y=np.arange(5)
    for offset,key,color,label in [(-.16,'V2/V2-Z','#218c8d','V2 / V2-Z'),(.16,'V2-Z/HV-A','#d66d35','V2-Z / H-V')]:
        means=np.array([r['contrasts'][key]['geomean'] for r in rows]);ci=np.array([r['contrasts'][key]['bootstrap95_conditional'] for r in rows]);a.errorbar(means,y+offset,xerr=np.array([means-ci[:,0],ci[:,1]-means]),fmt='o',color=color,capsize=3,label=label)
    a.axvline(1,color='gray',ls='--',lw=1);a.set_yticks(y,names);a.invert_yaxis();a.set_xlabel('Formal full-call speed ratio (>1: denominator faster)');a.legend(fontsize=8);a.set_title('(a) Zero-window and remaining H-V effects',fontsize=10);a.grid(axis='x',alpha=.2)
    a=axes[1];labels=[];vals=[]
    for name,r in zip(names,rows):
        for l in ['V2','V2-Z','HV-A']:
            labels.append(name+'  '+l);e=next(t for t in r['events'] if t['label']==l);vals.append(e['component_median_of_processes_us'][:4])
    vals=np.array(vals);positions=np.arange(15);left=np.zeros(15)
    for j,label,color in [(0,'Output-clear interval','#b8d5de'),(1,'Packed-clear interval','#87b5be'),(2,'Main incl. B gather','#416e99'),(3,'Restore','#d49156')]:
        a.barh(positions,vals[:,j],left=left,color=color,label=label,height=.72);left+=vals[:,j]
    a.set_yticks(positions,labels,fontsize=7);a.invert_yaxis();a.set_xlabel('Separate event diagnostics (us; instrumentation present)');a.set_title('(b) Stream event intervals (incl. submission gaps)',fontsize=10);a.legend(fontsize=7,loc='lower right');a.grid(axis='x',alpha=.2)
    target=D/'figures';target.mkdir(exist_ok=True)
    for ext in ['png','pdf']:fig.savefig(target/('d1-zero-and-costs.'+ext),dpi=220)
    plt.close(fig)
if __name__=='__main__':main()
