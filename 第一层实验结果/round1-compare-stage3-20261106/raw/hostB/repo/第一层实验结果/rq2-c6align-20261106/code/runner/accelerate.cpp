#include <algorithm>
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
 int n; vector<vector<int>> a,s; vector<int> deg;
 Graph(int n_,const int64_t* p,const int32_t* c):n(n_),a(n),s(n),deg(n){
  for(int v=0;v<n;v++){a[v]=vector<int>(c+p[v],c+p[v+1]);s[v]=a[v];sort(s[v].begin(),s[v].end());deg[v]=a[v].size();}
 }
 double sim(int u,int v)const{int i=0,j=0,z=0;while(i<(int)s[u].size()&&j<(int)s[v].size()){if(s[u][i]==s[v][j]){z++;i++;j++;}else if(s[u][i]<s[v][j])i++;else j++;}int den=deg[u]+deg[v]-z;return den?double(z)/den:1.;}
 vector<int> rabbit()const{
  vector<vector<int>> cols=s,rows=s;auto cmp=[&](int u,int v){return deg[u]!=deg[v]?deg[u]>deg[v]:u<v;};
  for(auto& x:cols)sort(x.begin(),x.end(),cmp);for(auto& x:rows)sort(x.begin(),x.end(),cmp);
  vector<int> roots(n),order; iota(roots.begin(),roots.end(),0);sort(roots.begin(),roots.end(),cmp);
  vector<char> queued(n),colseen(n);queue<int> q;
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
   touched.clear();for(int c:a[v])for(int u:a[c]){if(counts[u]++==0)touched.push_back(u);}
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
 vector<int> gorder(int W,double beta)const{
  vector<int64_t> score(n);vector<char> placed(n);vector<int> order;int cur=max_element(deg.begin(),deg.end())-deg.begin();double thr=sqrt(double(n));
  auto upd=[&](int u,int sign){for(int x:a[u])if(deg[x]<=thr)for(int v:a[x])score[v]+=sign;if(beta)for(int v:a[u])score[v]+=llround(2*beta)*sign;};
  for(int step=0;step<n;step++){order.push_back(cur);placed[cur]=1;upd(cur,1);if((int)order.size()>W-1)upd(order[order.size()-W],-1);if(step==n-1)break;
   int best=-1;int64_t value=-1;for(int v=0;v<n;v++)if(!placed[v]&&score[v]>value){best=v;value=score[v];}if(value<=0){int d=-1;for(int v=0;v<n;v++)if(!placed[v]&&deg[v]>d){best=v;d=deg[v];}}cur=best;
  }return order;
 }
 void bp_split(const int* vertices,int size,int s1,int iters,const double* L,int* sideout)const{
  vector<int> side(size);for(int i=s1;i<size;i++)side[i]=1;
  vector<vector<int>> cnt(2,vector<int>(n));vector<double> gain(size);
  auto cost=[&](int d,int sz){return d?d*(L[sz]-L[d+1]):0.;};
  for(int it=0;it<iters;it++){
   fill(cnt[0].begin(),cnt[0].end(),0);fill(cnt[1].begin(),cnt[1].end(),0);for(int i=0;i<size;i++)for(int q:a[vertices[i]])cnt[side[i]][q]++;
   vector<int> left,right;for(int i=0;i<size;i++){int x=side[i],y=1-x,na=x?size-s1:s1,nb=x?s1:size-s1;double z=0;for(int q:a[vertices[i]]){int da=cnt[x][q],db=cnt[y][q];z+=cost(da,na)+cost(db,nb)-cost(da-1,na)-cost(db+1,nb);}gain[i]=z;(x?right:left).push_back(i);}
   auto cmp=[&](int i,int j){return gain[i]>gain[j];};stable_sort(left.begin(),left.end(),cmp);stable_sort(right.begin(),right.end(),cmp);int moved=0;
   for(int k=0;k<(int)min(left.size(),right.size());k++){int x=left[k],y=right[k];if(gain[x]+gain[y]>0){side[x]=1;side[y]=0;moved++;}else break;}if(!moved)break;
  }copy(side.begin(),side.end(),sideout);
 }
};
struct LS{
 Graph* g;int n,W,K;vector<vector<int>> groups;vector<int> resid,part,gid,loc;vector<unordered_map<int,int>> cnt,blk;vector<unordered_set<int>> colwins;int64_t U=0,G=0;
 LS(Graph* g_,const int* order,int W_,int tau):g(g_),n(g->n),W(W_),part(n),gid(n,-1),loc(n),colwins(n){
  vector<int> kept;for(int i=0;i<n;i++)(tau<0||g->deg[order[i]]>tau?kept:resid).push_back(order[i]);
  K=(kept.size()+W-1)/W;groups.resize(K);cnt.resize(K);blk.resize(K);
  int z=0;for(int v:kept){int p=z/W;part[v]=p;gid[v]=p;loc[v]=groups[p].size();groups[p].push_back(v);z++;}for(int v:resid)part[v]=z++/W;
  for(int p=0;p<K;p++){for(int v:groups[p])for(int c:g->a[v])cnt[p][c]++;for(auto [c,k]:cnt[p]){colwins[c].insert(p);blk[p][part[c]]++;}U+=cnt[p].size();G+=blk[p].size();}
 }
 void bchg(int p,int h,int d){auto it=blk[p].find(h);int old=it==blk[p].end()?0:it->second,neu=old+d;if(neu==0){blk[p].erase(h);G--;}else{blk[p][h]=neu;if(old==0)G++;}}
 void colremove(int c){for(int p:colwins[c])bchg(p,part[c],-1);}
 void coladd(int c){for(int p:colwins[c])bchg(p,part[c],1);}
 void cchg(int p,int c,int d,int u,int v){auto it=cnt[p].find(c);int old=it==cnt[p].end()?0:it->second,neu=old+d;if(neu==0){cnt[p].erase(c);colwins[c].erase(p);U--;if(c!=u&&c!=v)bchg(p,part[c],-1);}else{cnt[p][c]=neu;if(old==0){colwins[c].insert(p);U++;if(c!=u&&c!=v)bchg(p,part[c],1);}}}
 void swapv(int u,int v){int p=gid[u],q=gid[v];if(p==q)return;colremove(u);colremove(v);for(int c:g->a[u]){cchg(p,c,-1,u,v);cchg(q,c,1,u,v);}for(int c:g->a[v]){cchg(q,c,-1,u,v);cchg(p,c,1,u,v);}std::swap(part[u],part[v]);int lu=loc[u],lv=loc[v];groups[p][lu]=v;groups[q][lv]=u;loc[u]=lv;loc[v]=lu;gid[u]=q;gid[v]=p;coladd(u);coladd(v);}
 int sweep(const int* verts,int nv,double lam){int accepted=0;vector<int> scores(K),touched;for(int i=0;i<nv;i++){int u=verts[i],p=gid[u];touched.clear();for(int c:g->a[u])for(int q:colwins[c])if(q!=p){if(scores[q]++==0)touched.push_back(q);}
   int top=min(3,(int)touched.size());partial_sort(touched.begin(),touched.begin()+top,touched.end(),[&](int x,int y){return scores[x]!=scores[y]?scores[x]>scores[y]:x<y;});bool done=false;
   for(int j=0;j<top&&!done;j++){int q=touched[j];auto candidates=groups[q];for(int v:candidates){int64_t oldU=U,oldG=G;swapv(u,v);if(double(U-oldU)+lam*double(G-oldG)<-1e-9){accepted++;done=true;break;}swapv(u,v);}}
   for(int q:touched)scores[q]=0;
  }return accepted;}
 vector<int> order()const{vector<int> o;for(auto&x:groups)o.insert(o.end(),x.begin(),x.end());o.insert(o.end(),resid.begin(),resid.end());return o;}
};
extern "C"{
 void* rq_graph(int n,const int64_t* p,const int32_t* c){return new Graph(n,p,c);}
 void rq_free_graph(void* p){delete static_cast<Graph*>(p);}
 void rq_order(void* p,int method,int W,double beta,int* out){auto*g=static_cast<Graph*>(p);vector<int> o;if(method==0)o=g->gorder(W,beta);else if(method==1)o=g->rsh();else if(method==2)o=g->rabbit();else o=g->neutron(W);copy(o.begin(),o.end(),out);}
 void rq_bp_split(void*p,const int*v,int size,int s1,int iters,const double*L,int*out){static_cast<Graph*>(p)->bp_split(v,size,s1,iters,L,out);}
 void* rq_ls(void*p,const int*o,int W,int tau){return new LS(static_cast<Graph*>(p),o,W,tau);}
 int rq_ls_sweep(void*p,const int*v,int n,double lam){return static_cast<LS*>(p)->sweep(v,n,lam);}
 void rq_ls_get(void*p,int*out,int64_t*ug){auto*s=static_cast<LS*>(p);auto o=s->order();copy(o.begin(),o.end(),out);ug[0]=s->U;ug[1]=s->G;}
 void rq_free_ls(void*p){delete static_cast<LS*>(p);}
}
