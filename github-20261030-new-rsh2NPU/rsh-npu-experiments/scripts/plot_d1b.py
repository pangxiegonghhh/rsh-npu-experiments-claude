"""Saved-data-only D1b paired backend and algorithm comparison figure."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d1b'
def main():
    rows=json.loads((D/'local_audit.json').read_text())['rows'];names=['ns3Da / 16','email-Enron / 64','ca-HepTh / 256','web-NotreDame / 16','thermal1 / 64'];fig,axes=plt.subplots(1,2,figsize=(12,4.7),layout='constrained');y=np.arange(5)
    sets=[[(f'Old-{v}/New-{v}',v,c) for v,c in [('V0','#527c99'),('V2','#21a093'),('V2-Z','#d89b3b')]]+ [('Old-HV/New-HV-A','H-V','#b35b6a')],[('New-V0/New-HV-A','New V0 / H-V','#527c99'),('New-V2/New-HV-A','New V2 / H-V','#21a093'),('New-V2-Z/New-HV-A','New V2-Z / H-V','#d89b3b')]]
    for panel,(ax,items) in enumerate(zip(axes,sets)):
        for j,(key,label,color) in enumerate(items):
            means=np.array([r['contrasts'][key]['geomean'] for r in rows]);ci=np.array([r['contrasts'][key]['bootstrap95_conditional'] for r in rows]);ax.errorbar(means,y+(j-(len(items)-1)/2)*.15,xerr=[means-ci[:,0],ci[:,1]-means],fmt='o',color=color,label=label,capsize=3,markersize=4)
        ax.axvline(1,color='gray',ls='--',lw=1);ax.set_yticks(y,names);ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.legend(fontsize=8);ax.set_xlabel('Full-call ratio (>1: denominator faster)');ax.set_title('(a) Runtime clear / native clear' if panel==0 else '(b) Algorithm comparisons with native clear',fontsize=10)
    out=D/'figures';out.mkdir(exist_ok=True)
    for ext in ['png','pdf']:fig.savefig(out/('d1b-native-clear.'+ext),dpi=220)
    plt.close(fig)
if __name__=='__main__':main()
