from pathlib import Path
import csv,json,statistics as st,math,re,collections
root=Path('results-blocks');reg=json.loads((root/'block-registration.json').read_text());valid=[x for x in reg if x['valid']];assert len(valid)==20
by=collections.defaultdict(lambda:collections.defaultdict(list));total=0
for block in valid:
 for x in csv.DictReader((Path(block['path'])/'samples/timing.csv').open()):by[x['case']][block['block']].append((int(x['batch']),float(x['us'])));total+=1
quality_root=Path('results-quality');quality_reg=json.loads((quality_root/'block-registration.json').read_text());qvalid=[x for x in quality_reg if x['valid']];assert len(qvalid)==20;quality_cases=set();quality_total=0
for block in qvalid:
 for x in csv.DictReader((Path(block['path'])/'samples/timing.csv').open()):
  case=x['case']
  if case not in quality_cases:by[case].clear();quality_cases.add(case)
  by[case][block['block']].append((int(x['batch']),float(x['us'])));quality_total+=1
summary={}
for case,blocks in by.items():
 slopes=[];r2s=[];inter=[]
 for block,rows in sorted(blocks.items()):
  assert len(rows)==4;x=[p[0] for p in rows];y=[p[1] for p in rows];xm=st.mean(x);ym=st.mean(y);s=sum((a-xm)*(b-ym) for a,b in rows)/sum((a-xm)**2 for a in x);c=ym-s*xm;ss=sum((b-ym)**2 for b in y);r2=1-sum((b-(c+s*a))**2 for a,b in rows)/ss;slopes.append(s);r2s.append(r2);inter.append(c)
 mean=st.mean(slopes);se=st.stdev(slopes)/math.sqrt(20);summary[case]=dict(case=case,mean_us_per_repeat=mean,ci_low=mean-2.093*se,ci_high=mean+2.093*se,min_r_squared=min(r2s),mean_r_squared=st.mean(r2s),slopes_by_block=slopes,intercept_mean_us=st.mean(inter))
pairs=[]
for case,a in summary.items():
 if '-merge-' not in case:continue
 b=summary[case.replace('-merge-','-split-')];seg=int(re.search(r'-s(\d+)-',case).group(1));diff=[y-x for x,y in zip(a['slopes_by_block'],b['slopes_by_block'])];d=st.mean(diff);se=st.stdev(diff)/math.sqrt(20);lo=d-2.093*se;hi=d+2.093*se
 pairs.append(dict(case=case,segments=seg,merge_us=a['mean_us_per_repeat'],split_us=b['mean_us_per_repeat'],speedup=b['mean_us_per_repeat']/a['mean_us_per_repeat'],saved_us=d,saved_ci_low=lo,saved_ci_high=hi,saved_ns_per_removed_api_call=d*1000/(seg-1) if seg>1 else None))
out=Path('analysis');out.mkdir(exist_ok=True);(out/'case-regressions.json').write_text(json.dumps(summary,indent=2));(out/'paired.json').write_text(json.dumps(pairs,indent=2))
with (out/'paired.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
groups=[]
for dt in ['f16','f32']:
 for api in ['nd','nz']:
  pp=[x for x in pairs if x['case'].startswith(dt+'-'+api+'-') and x['segments']>1];speeds=sorted(x['speedup'] for x in pp);groups.append(dict(dtype=dt,api=api,pairs=len(pp),ci_saved_positive=sum(x['saved_ci_low']>0 for x in pp),ci_saved_negative=sum(x['saved_ci_high']<0 for x in pp),speedup_min=min(speeds),speedup_median=st.median(speeds),speedup_max=max(speeds)))
res=dict(correctness_cases=688,valid_blocks=len(valid),invalid_blocks=len(reg)-len(valid),max_sentinel_drift=max(x['drift'] for x in valid),timing_samples_original=total,timing_samples_quality=quality_total,quality_cases=len(quality_cases),quality_invalid_blocks=len(quality_reg)-20,regression_cases=len(summary),case_mean_r2_below_0999=sum(x['mean_r_squared']<.999 for x in summary.values()),groups=groups);(out/'summary.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
for x in pairs:
 if '-s16-h1-gap8-' in x['case']:print('EXAMPLE',json.dumps(x))
