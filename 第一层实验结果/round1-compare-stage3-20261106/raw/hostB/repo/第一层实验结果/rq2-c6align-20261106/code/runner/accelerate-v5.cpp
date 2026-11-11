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
#include <cstdlib>
struct LS{
 Graph* g;int n,W,K,NB,Words;bool denseScores;vector<vector<int>> groups;vector<int> resid,part,gid,loc;
 vector<unordered_map<int,int>> cnt,positions;vector<vector<int>> colwins;vector<uint64_t> usedbits,blockAny,blockSingle;vector<uint16_t> blocks,overlap;int64_t U=0,G=0;
 vector<int> changeP,changeQ,touchedP,touchedQ;vector<char> markP,markQ;
 LS(Graph*g_,const int*order,int W_,int tau):g(g_),n(g->n),W(W_),NB((n+W-1)/W),part(n),gid(n,-1),loc(n),positions(n),colwins(n){
  vector<int> kept;for(int i=0;i<n;i++)(tau<0||g->deg[order[i]]>tau?kept:resid).push_back(order[i]);K=(kept.size()+W-1)/W;Words=(K+63)/64;
  groups.resize(K);cnt.resize(K);blocks.assign(size_t(K)*NB,0);usedbits.assign(size_t(n)*Words,0);blockAny.assign(size_t(NB)*Words,0);blockSingle.assign(size_t(NB)*Words,0);denseScores=!getenv("RQ2_FORCE_SPARSE_OVERLAP")&&n<=100000&&size_t(n)*K<=300000000ULL;
  changeP.resize(NB);changeQ.resize(NB);markP.resize(NB);markQ.resize(NB);touchedP.reserve(NB);touchedQ.reserve(NB);
  if(denseScores){assert(*max_element(g->deg.begin(),g->deg.end())<=65535);overlap.assign(size_t(n)*K,0);}
  int z=0;for(int v:kept){int p=z/W;part[v]=p;gid[v]=p;loc[v]=groups[p].size();groups[p].push_back(v);z++;}for(int v:resid)part[v]=z++/W;
  for(int p=0;p<K;p++){for(int v:groups[p])for(int c:g->a[v])cnt[p][c]++;for(auto [c,k]:cnt[p]){cwadd(c,p);bchg(p,part[c],1);if(denseScores)for(int u:g->a[c])overlap[size_t(u)*K+p]++;}U+=cnt[p].size();}
 }
 void cwadd(int c,int p){positions[c][p]=colwins[c].size();colwins[c].push_back(p);usedbits[size_t(c)*Words+p/64]|=uint64_t(1)<<(p%64);}
 void cwremove(int c,int p){auto it=positions[c].find(p);assert(it!=positions[c].end());int index=it->second,last=colwins[c].back();colwins[c][index]=last;colwins[c].pop_back();positions[c].erase(it);if(last!=p)positions[c][last]=index;usedbits[size_t(c)*Words+p/64]&=~(uint64_t(1)<<(p%64));}
 int count(int w,int c)const{auto it=cnt[w].find(c);return it==cnt[w].end()?0:it->second;}
 int block(int w,int h)const{return blocks[size_t(w)*NB+h];}
 void bchg(int p,int h,int d){auto&x=blocks[size_t(p)*NB+h];int old=x,neu=old+d;assert(neu>=0&&neu<=W);x=neu;size_t at=size_t(h)*Words+p/64;uint64_t bit=uint64_t(1)<<(p%64);if(neu)blockAny[at]|=bit;else blockAny[at]&=~bit;if(neu==1)blockSingle[at]|=bit;else blockSingle[at]&=~bit;if(!old&&neu)G++;else if(old&&!neu)G--;}
 void colremove(int c){for(int p:colwins[c])bchg(p,part[c],-1);}
 void coladd(int c){for(int p:colwins[c])bchg(p,part[c],1);}
 void cchg(int p,int c,int d,int u,int v){auto it=cnt[p].find(c);int old=it==cnt[p].end()?0:it->second,neu=old+d;assert(neu>=0);
  if(neu==0){cnt[p].erase(c);cwremove(c,p);U--;if(denseScores)for(int x:g->a[c])overlap[size_t(x)*K+p]--;if(c!=u&&c!=v)bchg(p,part[c],-1);}
  else{cnt[p][c]=neu;if(old==0){cwadd(c,p);U++;if(denseScores)for(int x:g->a[c])overlap[size_t(x)*K+p]++;if(c!=u&&c!=v)bchg(p,part[c],1);}}
 }
 void swapv(int u,int v){int p=gid[u],q=gid[v];if(p==q)return;colremove(u);colremove(v);for(int c:g->a[u]){cchg(p,c,-1,u,v);cchg(q,c,1,u,v);}for(int c:g->a[v]){cchg(q,c,-1,u,v);cchg(p,c,1,u,v);}std::swap(part[u],part[v]);int lu=loc[u],lv=loc[v];groups[p][lu]=v;groups[q][lv]=u;loc[u]=lv;loc[v]=lu;gid[u]=q;gid[v]=p;coladd(u);coladd(v);}
 int64_t deltaU(int u,int v,int p,int q)const{
  auto&a=g->s[u];auto&b=g->s[v];size_t i=0,j=0;int64_t delta=0;
  while(i<a.size()||j<b.size()){int c,d;if(j==b.size()||(i<a.size()&&a[i]<b[j])){c=a[i++];d=-1;}else if(i==a.size()||b[j]<a[i]){c=b[j++];d=1;}else{i++;j++;continue;}int x=count(p,c),y=count(q,c);delta+=int(x+d>0)-int(x>0)+int(y-d>0)-int(y>0);}return delta;
 }
 int64_t rowGamma(int w,int u,int v,int p,int q,int sign)const{
  unordered_map<int,int> change;auto&a=g->s[u];auto&b=g->s[v];size_t i=0,j=0;
  while(i<a.size()||j<b.size()){int c,d;if(j==b.size()||(i<a.size()&&a[i]<b[j])){c=a[i++];d=-sign;}else if(i==a.size()||b[j]<a[i]){c=b[j++];d=sign;}else{i++;j++;continue;}if(c!=u&&c!=v){int old=count(w,c),delta=int(old+d>0)-int(old>0);if(delta)change[part[c]]+=delta;}}
  int edge=binary_search(a.begin(),a.end(),v),oldU=count(w,u),oldV=count(w,v);change[p]-=oldU>0;change[q]+=oldU+sign*edge>0;change[q]-=oldV>0;change[p]+=oldV-sign*edge>0;
  int64_t delta=0;for(auto[h,d]:change){int old=block(w,h);assert(old+d>=0);delta+=int(old+d>0)-int(old>0);}return delta;
 }
 int64_t deltaGamma(int u,int v,int p,int q)const{
  int64_t delta=0;const uint64_t*a=&usedbits[size_t(u)*Words],*b=&usedbits[size_t(v)*Words];
  for(int j=0;j<Words;j++){uint64_t value=a[j]^b[j];while(value){int bit=__builtin_ctzll(value),w=j*64+bit;value&=value-1;if(w==p||w==q)continue;bool isU=(a[j]>>bit)&1;int source=isU?p:q,dest=isU?q:p;delta-=block(w,source)==1;delta+=block(w,dest)==0;}}
  return delta+rowGamma(p,u,v,p,q,1)+rowGamma(q,u,v,p,q,-1);
 }
 pair<int64_t,int64_t> trialDelta(int u,int v,int p,int q){
  touchedP.clear();touchedQ.clear();auto addP=[&](int h,int d){if(!d)return;if(!markP[h]){markP[h]=1;touchedP.push_back(h);}changeP[h]+=d;};auto addQ=[&](int h,int d){if(!d)return;if(!markQ[h]){markQ[h]=1;touchedQ.push_back(h);}changeQ[h]+=d;};
  auto&a=g->s[u];auto&b=g->s[v];size_t i=0,j=0;int64_t du=0,dg=0;
  while(i<a.size()||j<b.size()){int c,d;if(j==b.size()||(i<a.size()&&a[i]<b[j])){c=a[i++];d=-1;}else if(i==a.size()||b[j]<a[i]){c=b[j++];d=1;}else{i++;j++;continue;}int x=count(p,c),y=count(q,c),dp=int(x+d>0)-int(x>0),dq=int(y-d>0)-int(y>0);du+=dp+dq;if(c!=u&&c!=v){addP(part[c],dp);addQ(part[c],dq);}}
  int edge=binary_search(a.begin(),a.end(),v),pu=count(p,u),pv=count(p,v),qu=count(q,u),qv=count(q,v);
  addP(p,-int(pu>0));addP(q,int(pu+edge>0));addP(q,-int(pv>0));addP(p,int(pv-edge>0));
  addQ(p,-int(qu>0));addQ(q,int(qu-edge>0));addQ(q,-int(qv>0));addQ(p,int(qv+edge>0));
  for(int h:touchedP){int old=block(p,h),d=changeP[h];assert(old+d>=0);dg+=int(old+d>0)-int(old>0);changeP[h]=0;markP[h]=0;}
  for(int h:touchedQ){int old=block(q,h),d=changeQ[h];assert(old+d>=0);dg+=int(old+d>0)-int(old>0);changeQ[h]=0;markQ[h]=0;}
  const uint64_t*ba=&usedbits[size_t(u)*Words],*bb=&usedbits[size_t(v)*Words],*bp=&blockAny[size_t(p)*Words],*bq=&blockAny[size_t(q)*Words],*sp=&blockSingle[size_t(p)*Words],*sq=&blockSingle[size_t(q)*Words];
  for(int z=0;z<Words;z++){uint64_t mask=~uint64_t(0);if(z==p/64)mask&=~(uint64_t(1)<<(p%64));if(z==q/64)mask&=~(uint64_t(1)<<(q%64));uint64_t onlyU=ba[z]&~bb[z]&mask,onlyV=bb[z]&~ba[z]&mask;dg+=__builtin_popcountll(onlyU&~bq[z])-__builtin_popcountll(onlyU&sp[z])+__builtin_popcountll(onlyV&~bp[z])-__builtin_popcountll(onlyV&sq[z]);}
  return {du,dg};
 }
 int sweep(const int*verts,int nv,double lam){int accepted=0;vector<int> scores(K),touched;
  for(int i=0;i<nv;i++){int u=verts[i],p=gid[u];vector<int> cands;
   if(denseScores){const uint16_t*row=&overlap[size_t(u)*K];for(int q=0;q<K;q++)if(q!=p&&row[q]){int at=0;while(at<(int)cands.size()&&(row[cands[at]]>row[q]||(row[cands[at]]==row[q]&&cands[at]<q)))at++;if(at<3){cands.insert(cands.begin()+at,q);if(cands.size()>3)cands.pop_back();}}}
   else{touched.clear();for(int c:g->a[u])for(int q:colwins[c])if(q!=p){if(scores[q]++==0)touched.push_back(q);}int top=min(3,(int)touched.size());partial_sort(touched.begin(),touched.begin()+top,touched.end(),[&](int x,int y){return scores[x]!=scores[y]?scores[x]>scores[y]:x<y;});cands.assign(touched.begin(),touched.begin()+top);for(int q:touched)scores[q]=0;}
   bool done=false;for(int q:cands){auto candidates=groups[q];for(int v:candidates){int64_t du,dg=0;if(lam){auto delta=trialDelta(u,v,p,q);du=delta.first;dg=delta.second;}else du=deltaU(u,v,p,q);if(double(du)+lam*double(dg)<-1e-9){int64_t oldU=U,oldG=G;swapv(u,v);assert(U==oldU+du);if(lam)assert(G==oldG+dg);accepted++;done=true;break;}}if(done)break;}
  }return accepted;
 }
 vector<int> order()const{vector<int> out;for(auto&x:groups)out.insert(out.end(),x.begin(),x.end());out.insert(out.end(),resid.begin(),resid.end());return out;}
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
