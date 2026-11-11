#include <algorithm>
#include <cstdint>
#include <numeric>
#include <queue>
#include <set>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using namespace std;
extern "C" int capacity_repair(int n,const int64_t*p,const int32_t*c,int k,int W,int32_t*label,int32_t*trace,int64_t*stats){
 vector<vector<int>>rows(k),inv(n);vector<unordered_map<int,int>>counts(k);vector<int>loc(n,-1),sz(k),target(k,W);vector<int>groups(k);iota(groups.begin(),groups.end(),0);
 for(int r=0;r<n;r++)if(label[r]>=0){int g=label[r];loc[r]=rows[g].size();rows[g].push_back(r);for(int64_t j=p[r];j<p[r+1];j++){counts[g][c[j]]++;inv[c[j]].push_back(r);}}
 sort(groups.begin(),groups.end(),[&](int a,int b){int ma=rows[a].empty()?n:*min_element(rows[a].begin(),rows[a].end()),mb=rows[b].empty()?n:*min_element(rows[b].begin(),rows[b].end());return rows[a].size()!=rows[b].size()?rows[a].size()>rows[b].size():ma<mb;});
 vector<int>rename(k);for(int i=0;i<k;i++)rename[groups[i]]=i;vector<vector<int>>ordered(k);vector<unordered_map<int,int>>ct(k);for(int g=0;g<k;g++){ordered[rename[g]]=move(rows[g]);ct[rename[g]]=move(counts[g]);}rows=move(ordered);counts=move(ct);int total=0;for(int r=0;r<n;r++)if(label[r]>=0){label[r]=rename[label[r]];total++;}target[k-1]=total-W*(k-1);for(int g=0;g<k;g++)sz[g]=rows[g].size();int64_t pre=0;for(auto&ct:counts)pre+=ct.size();
 set<int>under;vector<unordered_set<int>>undercols(n);for(int g=0;g<k;g++)if(sz[g]<target[g]){under.insert(g);for(auto kv:counts[g])undercols[kv.first].insert(g);}
 vector<int>version(n),besttarget(n,-1),overlap(k),touched;vector<vector<int>>bestrows(k);using E=tuple<int,int,int,int>;priority_queue<E,vector<E>,greater<E>>heap;
 auto over=[&](int r){int g=label[r];return g>=0&&sz[g]>target[g];};
 auto calc=[&](int r){version[r]++;if(!over(r)||under.empty())return;int source=label[r],removed=0;int best=*under.begin(),score=0;touched.clear();
  for(int64_t j=p[r];j<p[r+1];j++){int col=c[j];removed+=counts[source].at(col)==1;for(int t:undercols[col])if(overlap[t]++==0)touched.push_back(t);}
  for(int t:touched){if(overlap[t]>score||(overlap[t]==score&&t<best)){score=overlap[t];best=t;}overlap[t]=0;}
  int delta=int(p[r+1]-p[r])-score-removed;besttarget[r]=best;bestrows[best].push_back(r);heap.emplace(delta,r,best,version[r]);
 };
 for(int r=0;r<n;r++)if(over(r))calc(r);int moves=0;int64_t objective=pre;vector<int>mark(n),affected;int generation=0;
 while(!heap.empty()){
  auto [delta,r,to,v]=heap.top();heap.pop();if(v!=version[r]||!over(r))continue;if(!under.count(to)){calc(r);continue;}int from=label[r];generation++;affected.clear();auto affect=[&](int x){if(mark[x]!=generation&&over(x)){mark[x]=generation;affected.push_back(x);}};
  int at=loc[r],last=rows[from].back();rows[from][at]=last;loc[last]=at;rows[from].pop_back();loc[r]=rows[to].size();rows[to].push_back(r);sz[from]--;sz[to]++;label[r]=to;version[r]++;
  for(int64_t j=p[r];j<p[r+1];j++){int col=c[j];auto it=counts[from].find(col);if(--it->second==0)counts[from].erase(it);if(counts[to][col]++==0)undercols[col].insert(to);for(int x:inv[col])affect(x);}
  if(sz[to]==target[to]){under.erase(to);for(auto kv:counts[to])undercols[kv.first].erase(to);for(int x:bestrows[to])if(besttarget[x]==to)affect(x);bestrows[to].clear();}
  for(int x:affected)calc(x);trace[4*moves]=r;trace[4*moves+1]=from;trace[4*moves+2]=to;trace[4*moves+3]=delta;moves++;objective+=delta;
 }
 int64_t post=0;for(int g=0;g<k;g++){if(sz[g]!=target[g])return 2;post+=counts[g].size();}stats[0]=pre;stats[1]=post;stats[2]=moves;stats[3]=objective;return post==objective?0:3;
}
