#include <cstdlib>
struct LS{
 Graph* g;int n,W,K,NB,Words;bool denseScores;vector<vector<int>> groups;vector<int> resid,part,gid,loc;
 vector<unordered_map<int,int>> cnt,positions;vector<vector<int>> colwins;vector<uint64_t> usedbits,singlebits,blockAny,blockSingle;vector<uint16_t> blocks,overlap;int64_t U=0,G=0;
 vector<int> changeP,changeQ,touchedP,touchedQ;vector<char> markP,markQ;
 LS(Graph*g_,const int*order,int W_,int tau):g(g_),n(g->n),W(W_),NB((n+W-1)/W),part(n),gid(n,-1),loc(n),positions(n),colwins(n){
  vector<int> kept;for(int i=0;i<n;i++)(tau<0||g->deg[order[i]]>tau?kept:resid).push_back(order[i]);K=(kept.size()+W-1)/W;Words=(K+63)/64;
  groups.resize(K);cnt.resize(K);blocks.assign(size_t(K)*NB,0);usedbits.assign(size_t(n)*Words,0);singlebits.assign(size_t(n)*Words,0);blockAny.assign(size_t(NB)*Words,0);blockSingle.assign(size_t(NB)*Words,0);denseScores=!getenv("RQ2_FORCE_SPARSE_OVERLAP")&&n<=100000&&size_t(n)*K<=300000000ULL;
  changeP.resize(NB);changeQ.resize(NB);markP.resize(NB);markQ.resize(NB);touchedP.reserve(NB);touchedQ.reserve(NB);
  if(denseScores){assert(*max_element(g->deg.begin(),g->deg.end())<=65535);overlap.assign(size_t(n)*K,0);}
  int z=0;for(int v:kept){int p=z/W;part[v]=p;gid[v]=p;loc[v]=groups[p].size();groups[p].push_back(v);z++;}for(int v:resid)part[v]=z++/W;
  for(int p=0;p<K;p++){for(int v:groups[p])for(int c:g->a[v])cnt[p][c]++;for(auto [c,k]:cnt[p]){cwadd(c,p);if(k==1)singlebits[size_t(c)*Words+p/64]|=uint64_t(1)<<(p%64);bchg(p,part[c],1);if(denseScores)for(int u:g->a[c])overlap[size_t(u)*K+p]++;}U+=cnt[p].size();}
 }
 void cwadd(int c,int p){positions[c][p]=colwins[c].size();colwins[c].push_back(p);usedbits[size_t(c)*Words+p/64]|=uint64_t(1)<<(p%64);}
 void cwremove(int c,int p){auto it=positions[c].find(p);assert(it!=positions[c].end());int index=it->second,last=colwins[c].back();colwins[c][index]=last;colwins[c].pop_back();positions[c].erase(it);if(last!=p)positions[c][last]=index;usedbits[size_t(c)*Words+p/64]&=~(uint64_t(1)<<(p%64));}
 int count(int w,int c)const{auto it=cnt[w].find(c);return it==cnt[w].end()?0:it->second;}
 int smallcount(int w,int c)const{size_t i=size_t(c)*Words+w/64;uint64_t bit=uint64_t(1)<<(w%64);return !(usedbits[i]&bit)?0:((singlebits[i]&bit)?1:2);}
 int block(int w,int h)const{return blocks[size_t(w)*NB+h];}
 void bchg(int p,int h,int d){auto&x=blocks[size_t(p)*NB+h];int old=x,neu=old+d;assert(neu>=0&&neu<=W);x=neu;size_t at=size_t(h)*Words+p/64;uint64_t bit=uint64_t(1)<<(p%64);if(neu)blockAny[at]|=bit;else blockAny[at]&=~bit;if(neu==1)blockSingle[at]|=bit;else blockSingle[at]&=~bit;if(!old&&neu)G++;else if(old&&!neu)G--;}
 void colremove(int c){for(int p:colwins[c])bchg(p,part[c],-1);}
 void coladd(int c){for(int p:colwins[c])bchg(p,part[c],1);}
 void cchg(int p,int c,int d,int u,int v){auto it=cnt[p].find(c);int old=it==cnt[p].end()?0:it->second,neu=old+d;assert(neu>=0);
  size_t si=size_t(c)*Words+p/64;uint64_t sb=uint64_t(1)<<(p%64);if(neu==1)singlebits[si]|=sb;else singlebits[si]&=~sb;
  if(neu==0){cnt[p].erase(c);cwremove(c,p);U--;if(denseScores)for(int x:g->a[c])overlap[size_t(x)*K+p]--;if(c!=u&&c!=v)bchg(p,part[c],-1);}
  else{cnt[p][c]=neu;if(old==0){cwadd(c,p);U++;if(denseScores)for(int x:g->a[c])overlap[size_t(x)*K+p]++;if(c!=u&&c!=v)bchg(p,part[c],1);}}
 }
 void swapv(int u,int v){int p=gid[u],q=gid[v];if(p==q)return;colremove(u);colremove(v);for(int c:g->a[u]){cchg(p,c,-1,u,v);cchg(q,c,1,u,v);}for(int c:g->a[v]){cchg(q,c,-1,u,v);cchg(p,c,1,u,v);}std::swap(part[u],part[v]);int lu=loc[u],lv=loc[v];groups[p][lu]=v;groups[q][lv]=u;loc[u]=lv;loc[v]=lu;gid[u]=q;gid[v]=p;coladd(u);coladd(v);}
 int64_t deltaU(int u,int v,int p,int q)const{
  auto&a=g->s[u];auto&b=g->s[v];size_t i=0,j=0;int64_t delta=0;
  while(i<a.size()||j<b.size()){int c,d;if(j==b.size()||(i<a.size()&&a[i]<b[j])){c=a[i++];d=-1;}else if(i==a.size()||b[j]<a[i]){c=b[j++];d=1;}else{i++;j++;continue;}int x=smallcount(p,c),y=smallcount(q,c);delta+=int(x+d>0)-int(x>0)+int(y-d>0)-int(y>0);}return delta;
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
  while(i<a.size()||j<b.size()){int c,d;if(j==b.size()||(i<a.size()&&a[i]<b[j])){c=a[i++];d=-1;}else if(i==a.size()||b[j]<a[i]){c=b[j++];d=1;}else{i++;j++;continue;}int x=smallcount(p,c),y=smallcount(q,c),dp=int(x+d>0)-int(x>0),dq=int(y-d>0)-int(y>0);du+=dp+dq;if(c!=u&&c!=v){addP(part[c],dp);addQ(part[c],dq);}}
  int edge=binary_search(a.begin(),a.end(),v),pu=smallcount(p,u),pv=smallcount(p,v),qu=smallcount(q,u),qv=smallcount(q,v);
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
