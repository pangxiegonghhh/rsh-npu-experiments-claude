"""Validate native mixed task evidence; do not infer temporal overlap ratio."""
from pathlib import Path
import csv,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.hv_cases import digest,save

def main()->None:
    dest=ROOT/'results/hv';paths=list((dest/'profile').rglob('op_summary*.csv'));assert len(paths)==1
    rows=list(csv.DictReader(paths[0].open()));mixed=[r for r in rows if r['Op Name']=='rsh_mix'];assert len(mixed)==5
    for r in mixed:
        assert r['Task Type']=='MIX_AIC' and int(r['Block Num'])==24 and int(r['Mix Block Num'])==48
        assert float(r['aic_mac_time(us)'])>0 and float(r['aiv_vec_time(us)'])>0
    case=json.loads((dest/'profile_case.json').read_text());assert case['correctness'] and case['records'][0]['cube_groups']>0 and case['records'][0]['aiv_rows']>0
    result={'passed':True,'executable_sha256':digest(ROOT/'build_v4/rsh_runner'),'profile_summary':str(paths[0].relative_to(ROOT)),'profile_summary_sha256':digest(paths[0]),'mixed_tasks':len(mixed),'task_type':'MIX_AIC','aic_blocks':24,'aiv_blocks':48,'all_tasks_aic_mac_and_aiv_vector_active':True,'numerical_correctness_both_paths':True,'native_mixed_dispatch_verified':True,'temporal_overlap_ratio_measured':False,'scope':'Same native mixed task has nonzero AIC MAC and AIV vector counters; not a separate sequential Cube then AIV replacement. Exact lane-level overlap fraction not resolved.'}
    save(dest/'mixed_validation.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
