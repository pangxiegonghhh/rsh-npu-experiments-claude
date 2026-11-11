import ast,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def audit():
 index={}
 for root in [BASE/'logs/source-snapshots',BASE/'scripts']:
  for p in root.rglob('*'):
   if p.is_file() and p.suffix in ['.py','.cpp','.c','.ini','.plist']:index.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(),str(p))
 required={};commands=0
 for p in (BASE/'logs').glob('stage3-*.command.json'):
  r=json.loads(p.read_text());hashes=r.get('source_sha256',{});command=r.get('command',[]);entries=[]
  for s in command:
   if not isinstance(s,str) or not s.endswith('.py'):continue
   q=Path(s)
   if q.is_absolute():
    try:s=q.relative_to(BASE).as_posix()
    except ValueError:continue
   if s in hashes:entries.append(s);break
  if not entries:continue
  commands+=1;seen=set();stack=entries[:]
  while stack:
   rel=stack.pop()
   if rel in seen or rel not in hashes:continue
   seen.add(rel);h=hashes[rel];item=required.setdefault((rel,h),dict(path=rel,sha256=h,source_snapshot=index.get(h),commands=[]));item['commands'].append(p.name)
   if h not in index:continue
   tree=ast.parse(Path(index[h]).read_text())
   for node in ast.walk(tree):
    names=[a.name.split('.')[0] for a in node.names] if isinstance(node,ast.Import) else [node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else []
    for module in names:
     local='scripts/'+module+'.py'
     if local in hashes:stack.append(local)
 missing=[v for v in required.values() if v['source_snapshot'] is None];result=dict(passed=not missing,commands_audited=commands,distinct_imported_source_versions=len(required),missing_source_versions=missing,source_versions=list(required.values()),scope='Python entrypoints and recursively declared local imports, matched byte-for-byte by recorded SHA-256; native binary/source hashes retained separately in artifact runtime manifests and port gates');(BASE/'logs/stage3-source-provenance-audit.json').write_text(json.dumps(result,indent=2));print('SOURCE_PROVENANCE',commands,len(required),'missing',len(missing));return result
if __name__=='__main__':
 r=audit()
 for x in r['missing_source_versions']:print(x['path'],x['sha256'],len(x['commands']))
