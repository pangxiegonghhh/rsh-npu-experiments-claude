#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <queue>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using namespace std;
struct Graph {
 int n,nc;vector<vector<int>> a,s,inv;vector<int> deg,orig,id;
 Graph(int nc_,const int64_t*p,const int32_t*c,int nr,const int32_t*K):n(nr),nc(nc_),a(n),s(n),inv(nc),deg(n),orig(K,K+nr),id(nc,-1){
  for(int v=0;v<n;v++){id[orig[v]]=v;a[v].assign(c+p[orig[v]],c+p[orig[v]+1]);s[v]=a[v];sort(s[v].begin(),s[v].end());deg[v]=a[v].size();for(int x:a[v])inv[x].push_back(v);}
 }
 double sim(int u,int v)const{int i=0,j=0,z=0;while(i<(int)s[u].size()&&j<(int)s[v].size()){if(s[u][i]==s[v][j]){z++;i++;j++;}else if(s[u][i]<s[v][j])i++;else j++;}int den=deg[u]+deg[v]-z;return den?double(z)/den:1.;}
 vector<int> rabbit()const{
  vector<vector<int>> cols=s,rows=inv;auto cmp=[&](int u,int v){return deg[u]!=deg[v]?deg[u]>deg[v]:u<v;};
  for(auto& x:cols)sort(x.begin(),x.end(),[&](int c,int d){return inv[c].size()!=inv[d].size()?inv[c].size()>inv[d].size():c<d;});for(auto& x:rows)sort(x.begin(),x.end(),cmp);
  vector<int> roots(n),order; iota(roots.begin(),roots.end(),0);sort(roots.begin(),roots.end(),cmp);
  vector<char> queued(n),colseen(nc);queue<int> q;
  for(int root:roots){if(queued[root])continue;queued[root]=1;q.push(root);
   while(!q.empty()){int v=q.front();q.pop();order.push_back(v);for(int c:cols[v])if(!colseen[c]){colseen[c]=1;for(int u:rows[c])if(!queued[u]){queued[u]=1;q.push(u);}}}
  }return order;
 }
 vector<int> neutron(int W)const{
  auto coarse=rabbit();vector<int> out;
  for(int start=0;start<n;start+=8*W){vector<int> rem(coarse.begin()+start,coarse.begin()+min(n,start+8*W));
   while(!rem.empty()){int anchor=rem.front();rem.erase(rem.begin());out.push_back(anchor);for(int k=1;k<W&&!rem.empty();k++){int best=0;double score=-1;for(int i=0;i<(int)rem.size();i++){double x=sim(anchor,rem[i]);if(x>score){score=x;best=i;}}out.push_back(rem[best]);rem.erase(rem.begin()+best);}}
  }return out;
 }
 vector<int> rsh()const{
  vector<unordered_map<int,double>> edges(n);vector<int> counts(n),touched;
  for(int v=0;v<n;v++){
   touched.clear();for(int c:a[v])for(int u:inv[c]){if(counts[u]++==0)touched.push_back(u);}
   vector<pair<double,int>> cand;cand.reserve(touched.size());
   for(int u:touched){if(u!=v)cand.emplace_back(-double(counts[u])/(deg[v]+deg[u]-counts[u]),u);counts[u]=0;}
   int k=min(8,(int)cand.size());partial_sort(cand.begin(),cand.begin()+k,cand.end());
   for(int i=0;i<k;i++){int u=cand[i].second;double w=-cand[i].first;if(w>0){edges[v][u]=w;edges[u][v]=w;}}
  }
  vector<vector<int>> comps;vector<char> seen(n);
  for(int root=0;root<n;root++)if(!seen[root]){vector<int> stack{root},comp;seen[root]=1;while(!stack.empty()){int v=stack.back();stack.pop_back();comp.push_back(v);for(auto [u,w]:edges[v])if(!seen[u]){seen[u]=1;stack.push_back(u);}}sort(comp.begin(),comp.end());comps.push_back(move(comp));}
  sort(comps.begin(),comps.end(),[](const auto&x,const auto&y){return x.size()!=y.size()?x.size()>y.size():x[0]<y[0];});
  fill(seen.begin(),seen.end(),0);vector<vector<pair<double,int>>> tree(n);vector<int> out;
  for(auto& comp:comps){int root=comp[0];seen[root]=1;priority_queue<tuple<double,int,int>,vector<tuple<double,int,int>>,greater<tuple<double,int,int>>> pq;
   for(auto [u,w]:edges[root])pq.emplace(-w,u,root);
   while(!pq.empty()){auto [neg,v,parent]=pq.top();pq.pop();if(seen[v])continue;seen[v]=1;tree[parent].emplace_back(-neg,v);tree[v].emplace_back(-neg,parent);for(auto [u,w]:edges[v])if(!seen[u])pq.emplace(-w,u,v);}
   vector<pair<int,int>> stack{{root,-1}};while(!stack.empty()){auto [v,parent]=stack.back();stack.pop_back();out.push_back(v);auto nbr=tree[v];sort(nbr.begin(),nbr.end(),[](auto x,auto y){return x.first!=y.first?x.first>y.first:x.second<y.second;});for(auto it=nbr.rbegin();it!=nbr.rend();++it)if(it->second!=parent)stack.emplace_back(it->second,v);}
  }
  vector<int> noniso,iso;for(int v:out)if(edges[v].empty())iso.push_back(v);else noniso.push_back(v);sort(iso.begin(),iso.end());out=move(noniso);out.insert(out.end(),iso.begin(),iso.end());
  for(int pass=0;pass<2;pass++){bool changed=false;for(int i=0;i<n-2;i++)for(int j=i+1;j<min(n-1,i+8);j++){double old=0,neu=0;if(i){old+=1-sim(out[i-1],out[i]);neu+=1-sim(out[i-1],out[j]);}if(j+1<n){old+=1-sim(out[j],out[j+1]);neu+=1-sim(out[i],out[j+1]);}if(neu+1e-12<old){reverse(out.begin()+i,out.begin()+j+1);changed=true;}}if(!changed)break;}
  return out;
 }

 // ===== T4：rsh 的 α / k / 孤立行模式版本（原 rsh() 不动）=====
 vector<int> rsh_t4(double alpha,int K,int iso_mode)const{
  last_candidates=0; last_isolated=0; last_components=0;
  const bool Wt=(alpha!=0.0);
  vector<double> w(Wt?nc:0,0.0),wdeg(Wt?n:0,0.0);
  if(Wt){for(int j=0;j<nc;j++){size_t d=inv[j].size();w[j]=d?pow((double)d,-alpha):0.0;}
         for(int v=0;v<n;v++){double t=0;for(int j:s[v])t+=w[j];wdeg[v]=t;}}
  auto simw=[&](int u,int v)->double{
   if(!Wt)return sim(u,v);
   int i=0,j=0;double z=0;
   while(i<(int)s[u].size()&&j<(int)s[v].size()){if(s[u][i]==s[v][j]){z+=w[s[u][i]];i++;j++;}else if(s[u][i]<s[v][j])i++;else j++;}
   double den=wdeg[u]+wdeg[v]-z;return den>0?z/den:1.;};
  vector<unordered_map<int,double>> edges(n);vector<int> counts(n),touched;vector<double> wcnt(Wt?n:0,0.0);
  for(int v=0;v<n;v++){
   touched.clear();for(int c:a[v])for(int u:inv[c]){if(counts[u]++==0)touched.push_back(u);if(Wt)wcnt[u]+=w[c];}
   vector<pair<double,int>> cand;cand.reserve(touched.size());
   for(int u:touched){if(u!=v){double sc=Wt?-wcnt[u]/(wdeg[v]+wdeg[u]-wcnt[u]):-double(counts[u])/(deg[v]+deg[u]-counts[u]);cand.emplace_back(sc,u);}counts[u]=0;if(Wt)wcnt[u]=0;}
   last_candidates+=(long)cand.size();
   int kk=min(K,(int)cand.size());partial_sort(cand.begin(),cand.begin()+kk,cand.end());
   for(int i=0;i<kk;i++){int u=cand[i].second;double ww=-cand[i].first;if(ww>0){edges[v][u]=ww;edges[u][v]=ww;}}
  }
  vector<vector<int>> comps;vector<char> seen(n);
  for(int root=0;root<n;root++)if(!seen[root]){vector<int> stack{root},comp;seen[root]=1;while(!stack.empty()){int v=stack.back();stack.pop_back();comp.push_back(v);for(auto [u,ww]:edges[v])if(!seen[u]){seen[u]=1;stack.push_back(u);}}sort(comp.begin(),comp.end());comps.push_back(move(comp));}
  sort(comps.begin(),comps.end(),[](const auto&x,const auto&y){return x.size()!=y.size()?x.size()>y.size():x[0]<y[0];});
  fill(seen.begin(),seen.end(),0);vector<vector<pair<double,int>>> tree(n);vector<int> out;
  for(auto& comp:comps){int root=comp[0];seen[root]=1;priority_queue<tuple<double,int,int>,vector<tuple<double,int,int>>,greater<tuple<double,int,int>>> pq;
   for(auto [u,ww]:edges[root])pq.emplace(-ww,u,root);
   while(!pq.empty()){auto [neg,v,parent]=pq.top();pq.pop();if(seen[v])continue;seen[v]=1;tree[parent].emplace_back(-neg,v);tree[v].emplace_back(-neg,parent);for(auto [u,ww]:edges[v])if(!seen[u])pq.emplace(-ww,u,v);}
   vector<pair<int,int>> stack{{root,-1}};while(!stack.empty()){auto [v,parent]=stack.back();stack.pop_back();out.push_back(v);auto nbr=tree[v];sort(nbr.begin(),nbr.end(),[](auto x,auto y){return x.first!=y.first?x.first>y.first:x.second<y.second;});for(auto it=nbr.rbegin();it!=nbr.rend();++it)if(it->second!=parent)stack.emplace_back(it->second,v);}
  }
  vector<int> noniso,iso;for(int v:out)if(edges[v].empty())iso.push_back(v);else noniso.push_back(v);sort(iso.begin(),iso.end());out=move(noniso);out.insert(out.end(),iso.begin(),iso.end());
  for(int pass=0;pass<2;pass++){bool changed=false;for(int i=0;i<n-2;i++)for(int j=i+1;j<min(n-1,i+8);j++){double old=0,neu=0;if(i){old+=1-simw(out[i-1],out[i]);neu+=1-simw(out[i-1],out[j]);}if(j+1<n){old+=1-simw(out[j],out[j+1]);neu+=1-simw(out[i],out[j+1]);}if(neu+1e-12<old){reverse(out.begin()+i,out.begin()+j+1);changed=true;}}if(!changed)break;}
  last_components=(long)comps.size(); last_isolated=(long)iso.size();
  last_local_isolated=0;last_moved=0;
  if(iso_mode==1&&n>1){
   auto share=[&](int u,int v){int i=0,j=0;while(i<(int)s[u].size()&&j<(int)s[v].size()){if(s[u][i]==s[v][j])return true;if(s[u][i]<s[v][j])i++;else j++;}return false;};
   auto hasglob=[&](int r){for(int c:a[r])if(inv[c].size()>1)return true;return false;};
   vector<int> S;
   for(int i=0;i<n;i++){int r=out[i];if(!hasglob(r))continue;bool L=i>0&&share(out[i-1],r);bool R=i+1<n&&share(r,out[i+1]);if(!L&&!R)S.push_back(r);}
   last_local_isolated=(long)S.size();
   vector<int> nx(n,-1),pv(n,-1);for(int i=0;i<n;i++){if(i>0)pv[out[i]]=out[i-1];if(i+1<n)nx[out[i]]=out[i+1];}
   int head=out[0];
   for(int r:S){
    int best=-1;double bs=-1;
    for(int c:a[r])for(int u:inv[c])if(u!=r){double x=simw(r,u);if(x>bs||(x==bs&&u<best)){bs=x;best=u;}}
    if(best<0)continue;
    if(pv[r]>=0)nx[pv[r]]=nx[r];else head=nx[r];
    if(nx[r]>=0)pv[nx[r]]=pv[r];
    int after=nx[best];nx[best]=r;pv[r]=best;nx[r]=after;if(after>=0)pv[after]=r;
    last_moved++;
   }
   out.clear();for(int v=head;v>=0;v=nx[v])out.push_back(v);
  }
  return out;
 }
 mutable long last_local_isolated=0,last_moved=0,last_candidates=0,last_isolated=0,last_components=0;
 vector<int> gorder(int W,double beta)const{
  vector<int64_t>score(n),delta(n);vector<int>heap(n),loc(n),fallback(n),touched;vector<char>placed(n),mark(n);iota(heap.begin(),heap.end(),0);iota(loc.begin(),loc.end(),0);iota(fallback.begin(),fallback.end(),0);
  sort(fallback.begin(),fallback.end(),[&](int x,int y){return deg[x]!=deg[y]?deg[x]>deg[y]:x<y;});
  auto better=[&](int x,int y){return score[x]!=score[y]?score[x]>score[y]:x<y;};
  auto exchange=[&](int i,int j){swap(heap[i],heap[j]);loc[heap[i]]=i;loc[heap[j]]=j;};
  auto fix=[&](int v){int i=loc[v];if(i<0)return;while(i&&better(heap[i],heap[(i-1)/2])){exchange(i,(i-1)/2);i=(i-1)/2;}while(2*i+1<(int)heap.size()){int j=2*i+1;if(j+1<(int)heap.size()&&better(heap[j+1],heap[j]))j++;if(!better(heap[j],heap[i]))break;exchange(i,j);i=j;}};
  auto change=[&](int v,int d){delta[v]+=d;if(!mark[v]){mark[v]=1;touched.push_back(v);}};
  double thr=sqrt(double(n));auto upd=[&](int u,int sign){for(int c:a[u])if(inv[c].size()<=thr)for(int v:inv[c])change(v,sign);if(beta)for(int c:a[u])if(id[c]>=0)change(id[c],2*sign);};
  vector<int>order;int cur=fallback[0],fp=0;
  for(int step=0;step<n;step++){order.push_back(cur);placed[cur]=1;int at=loc[cur],last=heap.back();heap.pop_back();loc[cur]=-1;if(at<(int)heap.size()){heap[at]=last;loc[last]=at;fix(last);}upd(cur,1);if((int)order.size()>W-1)upd(order[order.size()-W],-1);
   for(int v:touched){score[v]+=delta[v];delta[v]=0;fix(v);mark[v]=0;}touched.clear();if(step==n-1)break;if(score[heap[0]]>0)cur=heap[0];else{while(placed[fallback[fp]])fp++;cur=fallback[fp];}
  }return order;
 }
 void bp_split(const int* vertices,int size,int s1,int iters,const double* L,int* sideout)const{
  vector<int> side(size);for(int i=s1;i<size;i++)side[i]=1;
  vector<vector<int>> cnt(2,vector<int>(nc));vector<double> gain(size);
  auto cost=[&](int d,int sz){return d?d*(L[sz]-L[d+1]):0.;};
  for(int it=0;it<iters;it++){
   fill(cnt[0].begin(),cnt[0].end(),0);fill(cnt[1].begin(),cnt[1].end(),0);for(int i=0;i<size;i++)for(int q:a[vertices[i]])cnt[side[i]][q]++;
   vector<int> left,right;for(int i=0;i<size;i++){int x=side[i],y=1-x,na=x?size-s1:s1,nb=x?s1:size-s1;double z=0;for(int q:a[vertices[i]]){int da=cnt[x][q],db=cnt[y][q];z+=cost(da,na)+cost(db,nb)-cost(da-1,na)-cost(db+1,nb);}gain[i]=z;(x?right:left).push_back(i);}
   auto cmp=[&](int i,int j){return gain[i]>gain[j];};stable_sort(left.begin(),left.end(),cmp);stable_sort(right.begin(),right.end(),cmp);int moved=0;
   for(int k=0;k<(int)min(left.size(),right.size());k++){int x=left[k],y=right[k];if(gain[x]+gain[y]>0){side[x]=1;side[y]=0;moved++;}else break;}if(!moved)break;
  }copy(side.begin(),side.end(),sideout);
 }
};

extern "C"{
 void* rect_make(int nc,const int64_t*p,const int32_t*c,int nr,const int32_t*K){return new Graph(nc,p,c,nr,K);}void rect_free(void*p){delete static_cast<Graph*>(p);}
 void rect_order(void*p,int method,int W,int32_t*out){auto*g=static_cast<Graph*>(p);vector<int>v;if(method==0||method==1)v=g->gorder(W,method==0);else if(method==2)v=g->rsh();else if(method==3)v=g->rabbit();else v=g->neutron(W);copy(v.begin(),v.end(),out);}
 void rect_bp(void*p,const int32_t*v,int size,int s1,int iters,const double*L,int32_t*out){static_cast<Graph*>(p)->bp_split(v,size,s1,iters,L,out);}
void rect_order_rsh(void*p,double alpha,int k,int iso,int32_t*out){auto*g=static_cast<Graph*>(p);auto v=g->rsh_t4(alpha,k,iso);copy(v.begin(),v.end(),out);}
long rect_last_local_isolated(void*p){return static_cast<Graph*>(p)->last_local_isolated;}
long rect_last_candidates(void*p){return static_cast<Graph*>(p)->last_candidates;}
long rect_last_isolated(void*p){return static_cast<Graph*>(p)->last_isolated;}
long rect_last_components(void*p){return static_cast<Graph*>(p)->last_components;}
long rect_last_moved(void*p){return static_cast<Graph*>(p)->last_moved;}
}
