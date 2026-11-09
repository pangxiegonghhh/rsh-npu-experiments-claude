#include <algorithm>
#include <cstdint>
#include <numeric>
#include <vector>
extern "C" void rq_slashburn(int n,const int64_t*ptr,const int32_t*cols,int k,int32_t*out,int32_t*sizes){
 std::vector<unsigned char>alive(n,1),seen(n);std::vector<int>front,gcc(n),degree(n);std::iota(gcc.begin(),gcc.end(),0);
 std::vector<std::vector<int>>back;
 while(int(gcc.size())>k){
  std::vector<int>hubs;hubs.reserve(gcc.size());
  for(int v=0;v<n;v++)if(alive[v]){int d=0;for(int64_t j=ptr[v];j<ptr[v+1];j++)d+=alive[cols[j]];degree[v]=d;hubs.push_back(v);}
  std::sort(hubs.begin(),hubs.end(),[&](int x,int y){return degree[x]!=degree[y]?degree[x]>degree[y]:x<y;});
  hubs.resize(k);for(int v:hubs){front.push_back(v);alive[v]=0;}
  std::fill(seen.begin(),seen.end(),0);std::vector<std::vector<int>>comps;
  for(int root=0;root<n;root++)if(alive[root]&&!seen[root]){
   std::vector<int>stack{root},component;seen[root]=1;
   while(!stack.empty()){int x=stack.back();stack.pop_back();component.push_back(x);for(int64_t j=ptr[x];j<ptr[x+1];j++){int y=cols[j];if(alive[y]&&!seen[y]){seen[y]=1;stack.push_back(y);}}}
   comps.push_back(std::move(component));
  }
  std::stable_sort(comps.begin(),comps.end(),[](const auto&x,const auto&y){return x.size()>y.size();});
  gcc=comps.empty()?std::vector<int>{}:std::move(comps[0]);std::vector<int>block;
  for(size_t i=1;i<comps.size();i++)for(int v:comps[i]){block.push_back(v);alive[v]=0;}
  back.push_back(std::move(block));
 }
 sizes[0]=front.size();sizes[1]=gcc.size();int at=0;for(int v:front)out[at++]=v;for(int v:gcc)out[at++]=v;
 for(auto i=back.rbegin();i!=back.rend();i++)for(int v:*i)out[at++]=v;
}
