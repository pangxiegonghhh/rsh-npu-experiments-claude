"""Offline D0 process-level gain/null and host CPU diagnostics."""
from pathlib import Path
import importlib.util,sys,os,json,math
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d0'
os.environ.setdefault('MPLCONFIGDIR',str(D/'.mpl-cache'))
for package in ['matplotlib','PIL','contourpy','cycler','fontTools','kiwisolver','pyparsing','dateutil','packaging']:
    if importlib.util.find_spec(package) is None:
        paths=list((Path.home()/'.cache/uv/archive-v0').glob('*/'+package+'/__init__.py'))
        if paths:sys.path.append(str(sorted(paths)[0].parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
x=json.loads((D/'local_audit.json').read_text());out=D/'figures';out.mkdir(exist_ok=True)
labels=[r['matrix'].replace('FEMLAB_','').replace('SNAP_','').replace('Schmid_','')+'\nN'+str(r['n']) for r in x['rows']]
fig,axes=plt.subplots(1,2,figsize=(12,4.4))
for i,row in enumerate(x['rows']):
    for offset,name,color in [(-.10,'V2/HV-A','#0072B2'),(.10,'HV-A/HV-B','#D55E00')]:
        a=row['contrasts'][name];ys=a['process_ratios'];positions=[i+offset+(j-4.5)*.01 for j in range(10)]
        axes[0].scatter(positions,ys,color=color,s=15,alpha=.7,label=name if i==0 else None)
        axes[0].plot([i+offset-.07,i+offset+.07],[a['geomean']]*2,color=color,lw=2)
for ax in axes:
    ax.set_xticks(range(5),labels,fontsize=8);ax.spines[['top','right']].set_visible(False)
axes[0].axhline(1,color='gray',ls='--',lw=1);axes[0].set_ylabel('Process paired median time ratio');axes[0].set_title('Ten processes: gain and same-implementation null');axes[0].legend(fontsize=8)
for offset,label,color in [(-.18,'V0','#999999'),(-.06,'V2','#009E73'),(.06,'HV-A','#0072B2'),(.18,'HV-B','#D55E00')]:
    for i,row in enumerate(x['rows']):
        rs=[r for r in x['process_records'] if r['matrix']==row['matrix'] and r['n']==row['n'] and r['label']==label]
        ys=[r['thread_cpu_wall_fraction_median'] for r in rs]
        axes[1].scatter([i+offset]*len(ys),ys,s=12,alpha=.6,color=color,label=label if i==0 else None)
axes[1].set_ylabel('Bracketing thread CPU / full-call wall');axes[1].set_title('Host CPU fraction is not device execution time');axes[1].legend(fontsize=8,ncol=2)
fig.text(.01,.015,'Dots: independent process summaries. Blue gain >1 favors H-V; orange null should be near1. All samples retained.\nHost CPU clocks bracket a slightly wider interval; telemetry only before/after each runner. No device events.',fontsize=8)
fig.tight_layout(rect=(0,.11,1,1));fig.savefig(out/'d0-gain-null-and-host.png',dpi=180,bbox_inches='tight');fig.savefig(out/'d0-gain-null-and-host.pdf',bbox_inches='tight')
print('D0 figures saved')
