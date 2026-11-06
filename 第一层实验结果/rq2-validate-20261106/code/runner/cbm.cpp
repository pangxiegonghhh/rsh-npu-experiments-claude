#include <algorithm>
#include <cstdint>
#include <numeric>
#include <unordered_map>
#include <vector>
using namespace std;
struct DSU {vector<int> p;DSU(int n):p(n){iota(p.begin(),p.end(),0);}int f(int x){while(p[x]!=x){p[x]=p[p[x]];x=p[x];}return x;}bool join(int a,int b){a=f(a);b=f(b);if(a==b)return false;p[a]=b;return true;}};
struct Edge {int weight,u,v;};
extern "C" int rq_cbm(int n,const int64_t* ptr,const int32_t* idx,const int32_t* order,int W,int64_t limit,int32_t* output,int64_t* stats){
 unordered_map<uint64_t,int> co;vector<int> stamp(n,-1),cols;int64_t operations=0;
 for(int start=0,win=0;start<n;start+=W,win++){
  cols.clear();for(int i=start;i<min(n,start+W);i++){int v=order[i];for(int64_t j=ptr[v];j<ptr[v+1];j++){int c=idx[j];if(stamp[c]!=win){stamp[c]=win;cols.push_back(c);}}}
  sort(cols.begin(),cols.end());for(size_t i=0;i<cols.size();i++)for(size_t j=i+1;j<cols.size();j++){
   operations++;uint64_t key=(uint64_t(uint32_t(cols[i]))<<32)|uint32_t(cols[j]);co[key]++;
   if((int64_t)co.size()>limit){stats[0]=co.size();stats[1]=operations;return 1;}
  }
 }
 stats[0]=co.size();stats[1]=operations;vector<Edge> edges;edges.reserve(co.size());for(auto [key,w]:co)edges.push_back({w,int(key>>32),int(uint32_t(key))});co.clear();co.rehash(0);
 sort(edges.begin(),edges.end(),[](const Edge&a,const Edge&b){if(a.weight!=b.weight)return a.weight>b.weight;if(a.u!=b.u)return a.u>b.u;return a.v>b.v;});
 DSU d(n);vector<int> deg(n),seen(n);vector<vector<int>> nbr(n);
 for(auto e:edges)if(deg[e.u]<2&&deg[e.v]<2&&d.join(e.u,e.v)){deg[e.u]++;deg[e.v]++;nbr[e.u].push_back(e.v);nbr[e.v].push_back(e.u);}
 int count=0;for(int root=0;root<n;root++)if(!seen[root]&&deg[root]!=2){int prev=-1,cur=root;while(cur!=-1){seen[cur]=1;output[count++]=cur;int next=-1;for(int v:nbr[cur])if(v!=prev&&!seen[v]){next=v;break;}prev=cur;cur=next;}}
 for(int v=0;v<n;v++)if(!seen[v])output[count++]=v;
 return count==n?0:2;
}
