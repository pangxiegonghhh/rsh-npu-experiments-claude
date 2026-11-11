#include <algorithm>
#include <cstdint>
#include <numeric>
#include <set>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using namespace std;
using Rows=vector<vector<int>>;
struct CandidateGraph{
 int n;Rows a;vector<int> ne,em,lastSizes;
 CandidateGraph(int n_,const int64_t*p,const int32_t*c):n(n_),a(n){for(int r=0;r<n;r++){a[r].assign(c+p[r],c+p[r+1]);sort(a[r].begin(),a[r].end());(a[r].empty()?em:ne).push_back(r);}}
 int intersection(int r,int s)const{size_t i=0,j=0;int z=0;while(i<a[r].size()&&j<a[s].size()){if(a[r][i]==a[s][j]){z++;i++;j++;}else if(a[r][i]<a[s][j])i++;else j++;}return z;}
};
Rows postP(Rows groups,int W,int64_t*st){
 Rows full,shorts,added,rem;
 for(auto&g:groups){sort(g.begin(),g.end());(g.size()==size_t(W)?full:shorts).push_back(move(g));}
 sort(shorts.begin(),shorts.end(),[](auto&a,auto&b){return a.size()!=b.size()?a.size()>b.size():a[0]<b[0];});
 vector<set<pair<int,int>>> bins(W);for(int i=0;i<(int)shorts.size();i++)bins[shorts[i].size()].emplace(shorts[i][0],i);
 vector<char> absorbed(shorts.size());int merges=0;
 for(int t=0;t<(int)shorts.size();t++)if(!absorbed[t]){
  absorbed[t]=1;auto g=shorts[t];bins[g.size()].erase({g[0],t});
  for(int sz=1;sz<W&&g.size()<size_t(W);sz++){
   if(g.size()+sz>size_t(W))break;
   while(!bins[sz].empty()&&g.size()+sz<=size_t(W)){
    auto [row,i]=*bins[sz].begin();bins[sz].erase(bins[sz].begin());absorbed[i]=1;merges++;g.insert(g.end(),shorts[i].begin(),shorts[i].end());
   }
  }
  sort(g.begin(),g.end());(g.size()==size_t(W)?added:rem).push_back(move(g));
 }
 sort(rem.begin(),rem.end(),[](auto&a,auto&b){return a.size()!=b.size()?a.size()>b.size():a[0]<b[0];});
 st[0]=full.size();st[1]=shorts.size();st[2]=merges;st[3]=added.size();st[4]=rem.size();
 full.insert(full.end(),added.begin(),added.end());full.insert(full.end(),rem.begin(),rem.end());int pos=0,cuts=0;for(auto&g:full){cuts+=pos/W!=(pos+g.size()-1)/W;pos+=g.size();}st[5]=cuts;return full;
}
Rows c3(CandidateGraph&g,int b,int W,int64_t*st){
 Rows fs(g.n),groups;vector<int> rep;vector<char> active;vector<vector<int>> inv((g.n+b-1)/b);vector<int> counts(g.n),touched;
 int64_t checked=0;
 for(int r:g.ne){auto&fr=fs[r];for(int c:g.a[r])if(fr.empty()||fr.back()!=c/b)fr.push_back(c/b);
  touched.clear();for(int c:fr)for(int gi:inv[c])if(active[gi]&&counts[gi]++==0)touched.push_back(gi);
  sort(touched.begin(),touched.end(),[&](int x,int y){return groups[x].size()!=groups[y].size()?groups[x].size()>groups[y].size():rep[x]<rep[y];});
  int chosen=-1;for(int gi:touched){checked++;int inter=counts[gi];if(5LL*inter>=int64_t(fr.size()+fs[rep[gi]].size()-inter)){chosen=gi;break;}}
  for(int gi:touched)counts[gi]=0;
  if(chosen<0){chosen=groups.size();groups.push_back({r});rep.push_back(r);active.push_back(1);for(int c:fr)inv[c].push_back(chosen);}else groups[chosen].push_back(r);
  if(groups[chosen].size()==size_t(W))active[chosen]=0;
 }st[6]=groups.size();st[7]=checked;return groups;
}
Rows pool(CandidateGraph&g,int variant,int W,int64_t*st){
 auto seq=g.ne;sort(seq.begin(),seq.end(),[&](int r,int s){return g.a[r][0]!=g.a[s][0]?g.a[r][0]<g.a[s][0]:r<s;});
 vector<char> assigned(g.n);vector<int> mark(g.n);int generation=0;size_t ptr=0;Rows groups;int64_t eval=0;
 while(true){while(ptr<seq.size()&&assigned[seq[ptr]])ptr++;if(ptr==seq.size())break;vector<int> cand;for(size_t i=ptr;i<seq.size()&&cand.size()<128;i++)if(!assigned[seq[i]])cand.push_back(seq[i]);
  int seed=cand[0],usz=g.a[seed].size();int64_t z=usz;generation++;for(int c:g.a[seed])mark[c]=generation;vector<int> grp{seed};assigned[seed]=1;
  while(grp.size()<size_t(W)){
   int best=-1;int64_t bn=0,bd=1;int bu=0;
   for(int r:cand)if(!assigned[r]){eval++;int inter=0;for(int c:g.a[r])inter+=mark[c]==generation;int u=usz+g.a[r].size()-inter;int64_t num=variant==2?inter:z+g.a[r].size(),den=variant==2?1:(variant==0?u:W*16LL*((u+15)/16));
    if(best<0||__int128(num)*bd>__int128(bn)*den||(__int128(num)*bd==__int128(bn)*den&&(g.a[r].size()>g.a[best].size()||(g.a[r].size()==g.a[best].size()&&r<best)))){best=r;bn=num;bd=den;bu=u;}}
   if(best<0)break;grp.push_back(best);assigned[best]=1;z+=g.a[best].size();usz=bu;for(int c:g.a[best])mark[c]=generation;
  }groups.push_back(move(grp));
 }st[6]=groups.size();st[7]=eval;st[8]=count_if(groups.begin(),groups.end(),[&](auto&x){return x.size()<size_t(W);});return groups;
}
struct Key{uint64_t v[4];bool operator==(const Key&o)const{return equal(v,v+4,o.v);}};
struct KH{size_t operator()(const Key&k)const{uint64_t h=0;for(auto v:k.v)h^=v+0x9e3779b97f4a7c15ULL+(h<<6)+(h>>2);return h;}};
Rows c2(CandidateGraph&g,int W,const uint64_t*params,int64_t*st){
 const uint64_t P=(1ULL<<61)-1;vector<uint64_t> sig(size_t(g.n)*128,P);
 for(int r:g.ne)for(int k=0;k<128;k++){uint64_t best=P;for(int c:g.a[r]){__uint128_t v=__uint128_t(params[2*k])*(uint64_t(c)+1)+params[2*k+1];uint64_t h=uint64_t(v&P)+uint64_t(v>>61);if(h>=P)h-=P;best=min(best,h);}sig[size_t(r)*128+k]=best;}
 unordered_set<uint64_t> pairs;
 for(int band=0;band<32;band++){
  unordered_map<Key,vector<int>,KH> buckets;for(int r:g.ne){Key key;copy_n(&sig[size_t(r)*128+band*4],4,key.v);buckets[key].push_back(r);}
  for(auto&kv:buckets){auto&v=kv.second;for(size_t i=0;i<v.size();i++)for(size_t j=i+1;j<v.size();j++){pairs.insert((uint64_t(v[i])<<32)|uint32_t(v[j]));if(pairs.size()>50000000ULL)throw runtime_error("C2 candidate pair safety cap 50000000 exceeded; no truncated output");}}
 }
 struct E{int inter,uni,r,s;};vector<E> edges;for(auto key:pairs){int r=key>>32,s=uint32_t(key),i=g.intersection(r,s),u=g.a[r].size()+g.a[s].size()-i;if(5LL*i>=u)edges.push_back({i,u,r,s});}st[7]=pairs.size();pairs.clear();pairs.rehash(0);
 sort(edges.begin(),edges.end(),[](auto&a,auto&b){int64_t x=int64_t(a.inter)*b.uni,y=int64_t(b.inter)*a.uni;return x!=y?x>y:tie(a.r,a.s)<tie(b.r,b.s);});
 vector<int> parent(g.n);iota(parent.begin(),parent.end(),0);Rows members(g.n);for(int r:g.ne)members[r]={r};auto find=[&](int r){while(parent[r]!=r){parent[r]=parent[parent[r]];r=parent[r];}return r;};vector<int> done;vector<char> complete(g.n);int merged=0,reject=0;
 for(auto e:edges){int a=find(e.r),b=find(e.s);if(a==b)continue;if(members[a].size()+members[b].size()>size_t(W)){reject++;continue;}if(make_pair(members[a].size(),a)<make_pair(members[b].size(),b))swap(a,b);parent[b]=a;members[a].insert(members[a].end(),members[b].begin(),members[b].end());members[b].clear();merged++;if(members[a].size()==size_t(W)){done.push_back(a);complete[a]=1;}}
 vector<int> roots;for(int r:g.ne)if(!members[r].empty()&&!complete[r])roots.push_back(r);sort(roots.begin(),roots.end(),[&](int a,int b){return *min_element(members[a].begin(),members[a].end())<*min_element(members[b].begin(),members[b].end());});Rows groups;for(int r:done)groups.push_back(move(members[r]));for(int r:roots)groups.push_back(move(members[r]));st[6]=groups.size();st[8]=edges.size();st[9]=merged;st[10]=reject;return groups;
}
extern "C"{
 void* cand_graph(int n,const int64_t*p,const int32_t*c){return new CandidateGraph(n,p,c);}void cand_free(void*p){delete static_cast<CandidateGraph*>(p);}
 int cand_order(void*p,int method,int W,int b,int useP,const uint64_t*params,int32_t*out,int64_t*st,char*err){
  try{auto&g=*static_cast<CandidateGraph*>(p);Rows groups;if(method==0)groups=c2(g,W,params,st);else if(method==1)groups=c3(g,b,W,st);else groups=pool(g,method-2,W,st);
   if(method<=1&&useP)groups=postP(move(groups),W,st);else if(method==1)for(auto&x:groups)sort(x.begin(),x.end());
   g.lastSizes.clear();for(auto&x:groups)g.lastSizes.push_back(x.size());st[11]=groups.size();int i=0;for(auto&x:groups)for(int r:x)out[i++]=r;for(int r:g.em)out[i++]=r;return i==g.n?0:2;
  }catch(const exception&e){string s=e.what();copy_n(s.c_str(),min(size_t(1023),s.size()+1),err);return 1;}
 }
 void cand_sizes(void*p,int32_t*out){auto&g=*static_cast<CandidateGraph*>(p);copy(g.lastSizes.begin(),g.lastSizes.end(),out);}
}
