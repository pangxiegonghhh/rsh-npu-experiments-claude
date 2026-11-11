#include <algorithm>
#include <cstdint>
#include <numeric>
#include <tuple>
#include <vector>
struct Edge{double d;int i,j;};
extern "C" void c1_forest(int n,const int64_t*p,const int32_t*c,const int32_t*nn,int k,int hamming,int32_t*out,int64_t*stats){
 std::vector<uint64_t> keys;keys.reserve(size_t(n)*k);for(int i=0;i<n;i++)for(int q=0;q<k;q++){int j=nn[size_t(i)*k+q];if(j<0||j>=n||j==i)continue;keys.push_back((uint64_t(std::min(i,j))<<32)|uint32_t(std::max(i,j)));}std::sort(keys.begin(),keys.end());keys.erase(std::unique(keys.begin(),keys.end()),keys.end());
 std::vector<Edge> edges;edges.reserve(keys.size());std::vector<int> degree(n);int64_t zeros=0;
 for(uint64_t key:keys){int i=key>>32,j=uint32_t(key);int64_t x=p[i],y=p[j];int intersection=0;while(x<p[i+1]&&y<p[j+1]){if(c[x]==c[y]){intersection++;x++;y++;}else if(c[x]<c[y])x++;else y++;}int64_t total=p[i+1]-p[i]+p[j+1]-p[j];double d=hamming?double(total-2*intersection):1.-double(intersection)/double(total-intersection);edges.push_back({d,i,j});degree[i]++;degree[j]++;zeros+=d==0.;}
 std::vector<uint64_t>().swap(keys);std::sort(edges.begin(),edges.end(),[](auto&a,auto&b){return std::tie(a.d,a.i,a.j)<std::tie(b.d,b.i,b.j);});std::vector<int> parent(n),size(n,1);std::iota(parent.begin(),parent.end(),0);auto find=[&](int x){while(parent[x]!=x){parent[x]=parent[parent[x]];x=parent[x];}return x;};std::vector<std::vector<std::pair<double,int>>> tree(n);
 for(auto&e:edges){int a=find(e.i),b=find(e.j);if(a==b)continue;if(size[a]<size[b])std::swap(a,b);parent[b]=a;size[a]+=size[b];tree[e.i].emplace_back(e.d,e.j);tree[e.j].emplace_back(e.d,e.i);}
 std::vector<std::vector<int>> components(n);for(int i=0;i<n;i++)components[find(i)].push_back(i);std::vector<int> roots;for(int r=0;r<n;r++)if(!components[r].empty())roots.push_back(r);std::sort(roots.begin(),roots.end(),[&](int a,int b){return components[a].size()!=components[b].size()?components[a].size()>components[b].size():components[a][0]<components[b][0];});int pos=0;
 for(int r:roots){int root=*std::min_element(components[r].begin(),components[r].end(),[&](int a,int b){return degree[a]!=degree[b]?degree[a]>degree[b]:a<b;});std::vector<std::pair<int,int>> stack{{root,-1}};while(!stack.empty()){auto [i,prev]=stack.back();stack.pop_back();out[pos++]=i;auto&neighbors=tree[i];std::sort(neighbors.begin(),neighbors.end(),std::greater<>());for(auto [d,j]:neighbors)if(j!=prev)stack.emplace_back(j,i);}}
 stats[0]=roots.size();stats[1]=edges.size();stats[2]=zeros;
}
