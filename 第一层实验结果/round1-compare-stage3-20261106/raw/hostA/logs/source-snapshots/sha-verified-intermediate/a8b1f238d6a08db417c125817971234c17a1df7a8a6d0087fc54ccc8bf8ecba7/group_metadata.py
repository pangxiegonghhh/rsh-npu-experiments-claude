def group_stats(member,extras,W=16):
 sizes=extras.get('evaluation_group_sizes',extras.get('target_sizes'))
 if sizes is None:return {}
 sizes=[int(x) for x in sizes if int(x)>0];pos=0;cuts=0
 for size in sizes:cuts+=pos//W!=(pos+size-1)//W;pos+=size
 full=sum(s==W for s in sizes);short=sum(s<W for s in sizes);P=(member.startswith('C2-') or member.startswith('C3-')) and member!='C3-W4-noP'
 result=dict(groups_after=len(sizes),short_after=short,groups_cut_by_windows=cuts,P='on' if P else 'off' if member=='C3-W4-noP' else 'not_applicable',group_boundary_source='saved actual generation/repair group sizes')
 if P:
  for key in ['groups_full_before','short_before','P_merges','P_new_full']:
   if key in extras:result[key]=extras[key]
 else:result.update(groups_full_before=full,short_before=short,P_merges=0,P_new_full=0)
 return result
