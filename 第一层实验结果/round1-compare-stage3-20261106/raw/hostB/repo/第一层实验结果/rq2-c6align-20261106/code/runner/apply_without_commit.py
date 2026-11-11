from pathlib import Path
import hashlib,json,subprocess
BASE=Path(__file__).resolve().parents[1];repo=BASE/'repo';package=BASE/'package/rsh_pkg15'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check_list(name):
    result=[]
    for line in (package/name).read_text().splitlines():
        if not line.strip():continue
        wanted,path=line.split('  ',1);actual=sha(repo/path);assert actual==wanted,(path,actual,wanted)
        result.append({'path':path,'sha256':actual})
    return result
head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
assert tree=='ff969ff7806c3eb5cdf0b1abbf954011b63ff95f'
assert not git('status','--porcelain')
before=check_list('pkg15-sha256-before.txt');patch=package/'pkg15-0001.patch'
assert sha(patch)=='96f44d14d05c404fc4410e04e68da0fc0c74d18ea853fba54b40f97e6b6e4aae'
commands=[]
for args in [('apply','--check','--index',str(patch)),('apply','--index','--whitespace=nowarn',str(patch))]:
    r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
    commands.append({'argv':r.args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    assert r.returncode==0,commands[-1]
after=check_list('pkg15-sha256-after.txt');posttree=git('write-tree')
assert posttree=='ca3af5408b13a8ec9a424452649ebe943a902d19'
assert git('rev-parse','HEAD')==head
record={'passed':True,'before_commit':head,'HEAD_after_apply':head,'before_tree':tree,'after_index_tree':posttree,
        'commits_created':0,'pushed':False,'adaptation':'git apply --index replaces supplied git am script under explicit user no-commit instruction',
        'before_files':before,'after_files':after,'commands':commands,'git_status':git('status','--porcelain'),'diff_stat':git('diff','--cached','--stat')}
(BASE/'logs/package-application.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print(json.dumps({k:record[k]for k in ['passed','before_commit','after_index_tree','commits_created','pushed','diff_stat']},ensure_ascii=False,indent=2))
