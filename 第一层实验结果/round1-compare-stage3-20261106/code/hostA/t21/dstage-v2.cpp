#include <algorithm>
#include <cassert>
#include <cstdint>
#include <numeric>
#include <tuple>
#include <thread>
#include <unordered_map>
#include <vector>
using namespace std;
struct DSU{vector<int> p;DSU(int n):p(n){iota(p.begin(),p.end(),0);}int find(int x){while(p[x]!=x){p[x]=p[p[x]];x=p[x];}return x;}bool join(int a,int b){a=find(a);b=find(b);if(a==b)return false;p[a]=b;return true;}};
struct Candidate{int weight,a,ea,b,eb;};
extern "C" int rq_dstage(int n,const int64_t* ptr,const int32_t* cols,const int32_t* input,int W,int tau,int exact,int32_t* output,int64_t* stats){
 vector<int> kept,resid;for(int i=0;i<n;i++){int v=input[i];(tau<0||ptr[v+1]-ptr[v]>tau?kept:resid).push_back(v);}
 int K=(kept.size()+W-1)/W,words=(K+63)/64;vector<vector<int>> groups(K);
 vector<uint64_t> bits(size_t(n)*words,0);
 for(int i=0;i<(int)kept.size();i++){int v=kept[i],w=i/W;groups[w].push_back(v);for(int64_t j=ptr[v];j<ptr[v+1];j++)bits[size_t(cols[j])*words+w/64]|=uint64_t(1)<<(w%64);}
 auto co=[&](int u,int v){int value=0;const uint64_t*a=&bits[size_t(u)*words],*b=&bits[size_t(v)*words];for(int j=0;j<words;j++)value+=__builtin_popcountll(a[j]&b[j]);return value;};
 auto process_groups=[&](int tid,int threads){vector<int> dp;vector<signed char> parent;
 for(int gi=tid;gi<K;gi+=threads){auto&g=groups[gi];int size=g.size();if(size<=1)continue;
  if(exact){assert(size<=16);int weight[16][16];for(int i=0;i<size;i++)for(int j=0;j<size;j++)weight[i][j]=i==j?0:co(g[i],g[j]);
   int F=1<<size;dp.assign(size_t(F)*size,-1);parent.assign(size_t(F)*size,-1);for(int i=0;i<size;i++)dp[size_t(1<<i)*size+i]=0;
   for(int m=1;m<F;m++)for(unsigned ib=m;ib;ib&=ib-1){int i=__builtin_ctz(ib),value=dp[size_t(m)*size+i];assert(value>=0);for(unsigned jb=(F-1)^m;jb;jb&=jb-1){int j=__builtin_ctz(jb),nm=m|1<<j,v=value+weight[i][j];size_t index=size_t(nm)*size+j;if(v>dp[index]){dp[index]=v;parent[index]=i;}}}
   int best=-1,last=0;for(int i=0;i<size;i++)if(dp[size_t(F-1)*size+i]>best){best=dp[size_t(F-1)*size+i];last=i;}
   vector<int> order(size);int mask=F-1,cur=last;for(int t=size-1;t>=0;t--){order[t]=g[cur];int p=parent[size_t(mask)*size+cur];mask&=~(1<<cur);cur=p;}g=std::move(order);
  }else{if(size<=2)continue;vector<tuple<int,int,int>> edges;for(int i=0;i<size;i++)for(int j=i+1;j<size;j++)edges.emplace_back(co(g[i],g[j]),i,j);sort(edges.begin(),edges.end(),greater<>());
   DSU d(size);vector<int> deg(size),seen(size);vector<vector<int>> nb(size);
   for(auto [w,i,j]:edges){if(w<=0)break;if(deg[i]<2&&deg[j]<2&&d.join(i,j)){deg[i]++;deg[j]++;nb[i].push_back(j);nb[j].push_back(i);}}
   vector<int> order;for(int root=0;root<size;root++)if(!seen[root]&&deg[root]!=2){int prev=-1,cur=root;while(cur!=-1){seen[cur]=1;order.push_back(g[cur]);int next=-1;for(int u:nb[cur])if(u!=prev&&!seen[u]){next=u;break;}prev=cur;cur=next;}}
   for(int i=0;i<size;i++)if(!seen[i])order.push_back(g[i]);g=std::move(order);
  }
 }
 };
 if(exact&&K>=64){thread other([&]{process_groups(0,2);});process_groups(1,2);other.join();}else process_groups(0,1);
 vector<int> tail;if(K&&groups.back().size()<size_t(W)){tail=groups.back();groups.pop_back();}
 int k=groups.size();vector<int> pg(n,-1),pe(n),points;for(int i=0;i<k;i++){pg[groups[i][0]]=i;pe[groups[i][0]]=0;points.push_back(groups[i][0]);if(groups[i].size()>1){pg[groups[i].back()]=i;pe[groups[i].back()]=1;points.push_back(groups[i].back());}}
 vector<Candidate> candidates;
 auto add=[&](int x,int y,int c){if(x>y)std::swap(x,y);int a=pg[x],b=pg[y];if(a!=b&&c>0)candidates.push_back({c,a,pe[x],b,pe[y]});};
 if(points.size()<=6000){for(size_t i=0;i<points.size();i++)for(size_t j=i+1;j<points.size();j++)if(pg[points[i]]!=pg[points[j]])add(points[i],points[j],co(points[i],points[j]));}
 else{
  vector<vector<int>> wp(K);for(int p:points)for(int j=0;j<words;j++){uint64_t value=bits[size_t(p)*words+j];while(value){int b=__builtin_ctzll(value),w=j*64+b;if(w<K)wp[w].push_back(p);value&=value-1;}}
  unordered_map<uint64_t,int> pairs;for(auto& pts:wp){sort(pts.begin(),pts.end());for(size_t i=0;i<pts.size();i++)for(size_t j=i+1;j<pts.size();j++){uint64_t key=(uint64_t(uint32_t(pts[i]))<<32)|uint32_t(pts[j]);pairs[key]++;}}
  candidates.reserve(pairs.size());for(auto [key,c]:pairs)add(int(key>>32),int(uint32_t(key)),c);
 }
 sort(candidates.begin(),candidates.end(),[](auto&a,auto&b){return tie(a.weight,a.a,a.ea,a.b,a.eb)>tie(b.weight,b.a,b.ea,b.b,b.eb);});
 DSU d(k);vector<int> used(2*k),seen(k);vector<vector<tuple<int,int,int>>> link(k);
 for(auto c:candidates){if(used[2*c.a+c.ea]||used[2*c.b+c.eb])continue;if(groups[c.a].size()==1&&!link[c.a].empty())continue;if(groups[c.b].size()==1&&!link[c.b].empty())continue;if(!d.join(c.a,c.b))continue;used[2*c.a+c.ea]=used[2*c.b+c.eb]=1;link[c.a].emplace_back(c.ea,c.b,c.eb);link[c.b].emplace_back(c.eb,c.a,c.ea);}
 vector<int> out;auto append=[&](int group,bool forward){if(forward)out.insert(out.end(),groups[group].begin(),groups[group].end());else out.insert(out.end(),groups[group].rbegin(),groups[group].rend());};
 for(int root=0;root<k;root++)if(!seen[root]&&link[root].size()!=2){bool forward=link[root].empty()||get<0>(link[root][0])==1||groups[root].size()==1;append(root,forward);int cur=root;seen[cur]=1;
  while(true){int next=-1,end=0;for(auto [ea,b,eb]:link[cur])if(!seen[b]){next=b;end=eb;break;}if(next<0)break;append(next,end==0||groups[next].size()==1);seen[next]=1;cur=next;}
 }
 for(int i=0;i<k;i++)if(!seen[i])append(i,true);out.insert(out.end(),tail.begin(),tail.end());out.insert(out.end(),resid.begin(),resid.end());assert(out.size()==size_t(n));copy(out.begin(),out.end(),output);
 stats[0]=K;stats[1]=points.size();stats[2]=candidates.size();stats[3]=words;return 0;
}
