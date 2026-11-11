#include <algorithm>
#include <cstdint>
#include <vector>
using namespace std;
extern "C" void large_rcm(int n,const int64_t*p,const int32_t*c,int32_t*out){vector<int>roots;vector<vector<int>>nb(n);auto key=[&](int a,int b){int64_t da=p[a+1]-p[a],db=p[b+1]-p[b];return da!=db?da<db:a<b;};for(int r=0;r<n;r++)if(p[r+1]>p[r]){roots.push_back(r);nb[r].assign(c+p[r],c+p[r+1]);sort(nb[r].begin(),nb[r].end(),key);}sort(roots.begin(),roots.end(),key);vector<char>seen(n);vector<int>order,q;for(int root:roots)if(!seen[root]){q.clear();q.push_back(root);seen[root]=1;for(size_t i=0;i<q.size();i++)for(int u:nb[q[i]])if(!seen[u]){seen[u]=1;q.push_back(u);}order.insert(order.end(),q.begin(),q.end());}int at=0;for(auto i=order.rbegin();i!=order.rend();i++)out[at++]=*i;for(int r=0;r<n;r++)if(p[r]==p[r+1])out[at++]=r;}
