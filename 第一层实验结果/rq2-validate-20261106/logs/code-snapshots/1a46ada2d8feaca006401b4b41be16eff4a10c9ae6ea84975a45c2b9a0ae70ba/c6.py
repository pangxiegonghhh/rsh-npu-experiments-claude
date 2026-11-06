"""Column-net recursive bisection, with explicit symmetric send/receive message nets."""
from __future__ import annotations
import collections,hashlib,json,math,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'deps'))

class ExactBalanceUnavailable(RuntimeError):pass

def reorder(adj:list[set[int]],W:int,mnc:int,trace_path:Path)->tuple[list[int],dict]:
    import kahypar
    n=len(adj);owner=[0]*n;parts={0:list(range(n))};queue=collections.deque([0]);tree={};nextid=1;trace=[];started=time.perf_counter()
    def checkpoint(status:str)->None:
        trace_path.parent.mkdir(parents=True,exist_ok=True)
        tmp=trace_path.with_suffix('.tmp');tmp.write_text(json.dumps({'status':status,'W':W,'mnc':mnc,'seed':0,'calls':trace,'elapsed_sec':time.perf_counter()-started},separators=(',',':')));tmp.replace(trace_path)
    while queue:
        pid=queue.popleft();vertices=parts[pid];size=len(vertices)
        if size<=W:continue
        s1=W*math.ceil(size/(2*W));s2=size-s1
        columns=collections.defaultdict(list);messages=collections.defaultdict(list)
        for local,v in enumerate(vertices):
            destinations=set()
            for c in adj[v]:
                columns[c].append(local)
                if mnc and pid!=0 and owner[c]!=pid:destinations.add(owner[c])
            for other in destinations:messages[other].append(local)
        nets=[];weights=[];num_column_nets=0;num_message_nets=0
        for c in sorted(columns):
            pins=columns[c]
            if len(pins)>1:nets.append(pins);weights.append(1);num_column_nets+=1
        for other in sorted(messages):
            pins=messages[other]
            if len(pins)>1:
                # A0 is structurally symmetric: send and receive pin sets coincide.
                nets.extend([pins,pins]);weights.extend([mnc,mnc]);num_message_nets+=2
        pointers=[0];flat=[]
        for pins in nets:flat.extend(pins);pointers.append(len(flat))
        call={'part_id':pid,'size':size,'targets':[s1,s2],'column_nets':num_column_nets,'message_nets':num_message_nets,'pins':len(flat),'hypergraph_sha256':hashlib.sha256(json.dumps([pointers,flat,weights],separators=(',',':')).encode()).hexdigest()}
        t=time.perf_counter()
        if not nets:labels=[0]*s1+[1]*s2;call['solver']='edgeless objective; deterministic feasible exact split'
        else:
            hypergraph=kahypar.Hypergraph(size,len(nets),pointers,flat,2,weights,[1]*size)
            context=kahypar.Context();context.loadINIconfiguration(str(BASE/'scripts/kahypar-cut-v1.3.7.ini'))
            context.setK(2);context.setEpsilon(0.0);context.setCustomTargetBlockWeights([s1,s2]);context.setSeed(0);context.suppressOutput(True)
            kahypar.partition(hypergraph,context);labels=[int(hypergraph.blockID(v)) for v in range(size)];call['solver']='KaHyPar 1.3.7, cut, custom exact target upper bounds, epsilon=0'
        left=[v for i,v in enumerate(vertices) if labels[i]==0];right=[v for i,v in enumerate(vertices) if labels[i]==1]
        call.update(actual_sizes=[len(left),len(right)],solver_sec=time.perf_counter()-t,weighted_cut=sum(w for pins,w in zip(nets,weights) if any(labels[v]!=labels[pins[0]] for v in pins)),labels_sha256=hashlib.sha256(json.dumps(labels).encode()).hexdigest())
        trace.append(call)
        if (len(left),len(right))!=(s1,s2):
            call['failure']='Exact target sizes not met; no manual rebalance and no relaxed acceptance.';call['vertices']=vertices;call['labels']=labels
            model=trace_path.with_name(trace_path.stem+'-failed-model.json');model.write_text(json.dumps({'vertices':vertices,'pointers':pointers,'pins':flat,'weights':weights,'labels':labels,'targets':[s1,s2]},separators=(',',':')));call['failed_model']=str(model);checkpoint('INCOMPLETE_EXACT_BALANCE')
            raise ExactBalanceUnavailable(f'part {pid}: requested {(s1,s2)}, returned {(len(left),len(right))}')
        lid,rid=nextid,nextid+1;nextid+=2;tree[pid]=(lid,rid);del parts[pid];parts[lid]=left;parts[rid]=right
        for v in left:owner[v]=lid
        for v in right:owner[v]=rid
        queue.extend([lid,rid])
        if len(trace)<=2 or len(trace)%100==0:print('C6 progress',mnc,len(trace),len(parts),flush=True);checkpoint('RUNNING')
    leaves=[];stack=[0]
    while stack:
        pid=stack.pop()
        if pid in tree:lid,rid=tree[pid];stack.extend([rid,lid])
        else:leaves.append(parts[pid])
    full=[x for x in leaves if len(x)==W];partial=[x for x in leaves if len(x)<W]
    assert len(partial)<=1 and len(full)+len(partial)==math.ceil(n/W)
    order=[v for part in full+partial for v in part];assert sorted(order)==list(range(n))
    checkpoint('OK')
    return order,{'implementation':'KaHyPar recursive bisection','W':W,'mnc':mnc,'seed':0,'epsilon':0.0,'group_sizes':[len(x) for x in full+partial],
                  'bisection_schedule':'breadth first; current parts define message destinations; final own order is DFS left/right with partial leaf last',
                  'column_nets':'all global A0 columns restricted to vertices in the current part, cost 1; degree<=1 nets omitted',
                  'message_nets':'each other current part: row vertices accessing that part; symmetric send/receive duplicate nets, each cost mnc; no root message nets',
                  'configuration':'code/runner/kahypar-cut-v1.3.7.ini','trace':str(trace_path),'partition_sec':time.perf_counter()-started}
