"""Render only the new R3/R4 tables; never write the original analysis directory."""
from pathlib import Path
import csv,os
import numpy as np

def render(root:Path)->None:
    os.environ.setdefault('MPLCONFIGDIR','/private/tmp/m11b-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=root/'figures';out.mkdir(exist_ok=True)
    labels=['FP16 N128','FP16 N256','FP32 N128','FP32 N256']
    rows=list(csv.DictReader((root/'R3-primary-cold-hot.csv').open()))
    fig,ax=plt.subplots(figsize=(10,4),layout='constrained')
    for p,offset in [(0,-.18),(1,0),(2,.18)]:
        current=[r for r in rows if r['case_id'].endswith(f'p{p}')]
        y=np.array([float(r['ratio']) for r in current]);lo=np.array([float(r['ci_low']) for r in current]);hi=np.array([float(r['ci_high']) for r in current])
        ax.errorbar(np.arange(4)+offset,y,yerr=[y-lo,hi-y],fmt='o',capsize=3,label=['ND2NZ','ordinary row','ordinary stripe'][p])
    ax.axhline(1,color='gray',ls='--');ax.set_xticks(range(4),labels);ax.set_ylabel('Cold / hot mean replay time');ax.set_title('Cora B1: cache sensitivity differs by path\n20 paired blocks; pointwise bootstrap 95% CI');ax.legend()
    for ext in ['png','pdf']:fig.savefig(out/f'R3-cache-sensitivity.{ext}',dpi=180)
    plt.close(fig)
    rows=list(csv.DictReader((root/'R4-hot-only-posthoc.csv').open()))
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    y=np.array([float(r['ratio']) for r in rows]);lo=np.array([float(r['ci_low']) for r in rows]);hi=np.array([float(r['ci_high']) for r in rows])
    ax.errorbar(range(4),y,yerr=[y-lo,hi-y],fmt='o',capsize=3)
    ax.axhline(1,color='gray',ls='--');ax.axhline(.8,color='black',ls=':');ax.set_xticks(range(4),labels);ax.set_ylabel('Ordinary row / ND2NZ mean time');ax.set_title('Post hoc hot-only sensitivity: 3/4 cells below 0.8\nOriginal registered denominator remains eight')
    for ext in ['png','pdf']:fig.savefig(out/f'R4-hot-only.{ext}',dpi=180)
    plt.close(fig)

if __name__=='__main__':render(Path(__file__).resolve().parent)
