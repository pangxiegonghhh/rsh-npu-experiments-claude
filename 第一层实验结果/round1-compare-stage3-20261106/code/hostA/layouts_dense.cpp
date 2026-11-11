#include <algorithm>
#include <cstdint>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>
using namespace std;
struct DS{vector<int>p;DS(int n):p(n){iota(p.begin(),p.end(),0);}int f(int x){while(x!=p[x]){p[x]=p[p[x]];x=p[x];}return x;}bool u(int a,int b){a=f(a);b=f(b);if(a==b)return false;p[a]=b;return true;}};
struct Context{
 int n,K,W,words;vector<vector<int>> a,w,cw;vector<vector<uint64_t>> bits;
 Context(int n_,const int64_t*p,const int32_t*c,const int32_t*flat,const int64_t*wp,int k,int W_,bool diag):n(n_),K(k),W(W_),words((k+63)/64),a(n),w(k),cw(n),bits(n){
  for(int r=0;r<n;r++){a[r].assign(c+p[r],c+p[r+1]);if(diag)a[r].push_back(r);}
  vector<int>mark(n,-1);for(int gi=0;gi<K;gi++){w[gi].assign(flat+wp[gi],flat+wp[gi+1]);for(int r:w[gi])for(int c:a[r])if(mark[c]!=gi){mark[c]=gi;cw[c].push_back(gi);}}
  for(int c=0;c<n;c++)if(cw[c].size()>size_t(2*words)){bits[c].assign(words,0);for(int gi:cw[c])bits[c][gi/64]|=uint64_t(1)<<(gi%64);}
 }
 int co(int x,int y)const{auto&a=cw[x];auto&b=cw[y];int z=0;
  if(!bits[x].empty()&&!bits[y].empty()){for(int j=0;j<words;j++)z+=__builtin_popcountll(bits[x][j]&bits[y][j]);}
  else if(!bits[x].empty()){for(int j:b)z+=(bits[x][j/64]>>(j%64))&1;}
  else if(!bits[y].empty()){for(int j:a)z+=(bits[y][j/64]>>(j%64))&1;}
  else{size_t i=0,j=0;while(i<a.size()&&j<b.size()){if(a[i]==b[j]){z++;i++;j++;}else if(a[i]<b[j])i++;else j++;}}return z;
 }
 template<class F>void pointpairs(vector<int>pts,bool guard,F consume,int64_t&skips){
  sort(pts.begin(),pts.end());pts.erase(unique(pts.begin(),pts.end()),pts.end());vector<vector<int>>wp(K);uint64_t enumerations=0;
  for(int x:pts)for(int wi:cw[x])wp[wi].push_back(x);
  for(auto&v:wp){if(guard&&v.size()>400){skips++;continue;}enumerations+=uint64_t(v.size())*(v.size()-1)/2;}
  double avg=0;for(int x:pts)avg+=min(size_t(words),cw[x].size());if(!pts.empty())avg/=pts.size();double direct=double(pts.size())*(pts.size()-1)/2*max(1.,avg);
  if(!guard&&(pts.size()<=6000||enumerations*7.>direct)){
   for(size_t i=0;i<pts.size();i++)for(size_t j=i+1;j<pts.size();j++){int z=co(pts[i],pts[j]);if(z)consume(pts[i],pts[j],z);}return;
  }
  unordered_map<uint64_t,int>pairs;for(auto&v:wp){if(guard&&v.size()>400)continue;for(size_t i=0;i<v.size();i++)for(size_t j=i+1;j<v.size();j++){pairs[(uint64_t(v[i])<<32)|uint32_t(v[j])]++;if(pairs.size()>100000000ULL)throw runtime_error("co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE");}}
  for(auto kv:pairs)consume(kv.first>>32,uint32_t(kv.first),kv.second);
 }
 vector<vector<int>> intra(){auto out=w;for(auto&g:out){int s=g.size();if(s<=2)continue;vector<tuple<int,int,int>>edges;for(int i=0;i<s;i++)for(int j=i+1;j<s;j++)edges.emplace_back(co(g[i],g[j]),i,j);sort(edges.begin(),edges.end(),greater<>());DS d(s);vector<int>degree(s),seen(s);vector<vector<int>>nb(s);
   for(auto [z,i,j]:edges){if(!z)break;if(degree[i]<2&&degree[j]<2&&d.u(i,j)){degree[i]++;degree[j]++;nb[i].push_back(j);nb[j].push_back(i);}}
   vector<int>order;for(int st=0;st<s;st++)if(!seen[st]&&degree[st]!=2){int prev=-1,cur=st;while(cur!=-1){seen[cur]=1;order.push_back(g[cur]);int next=-1;for(int x:nb[cur])if(x!=prev&&!seen[x]){next=x;break;}prev=cur;cur=next;}}for(int i=0;i<s;i++)if(!seen[i])order.push_back(g[i]);g=move(order);
  }return out;
 }
 vector<int> dense_inter(const vector<vector<int>>&groups,bool&enabled){
  enabled=false;int k=groups.size();if(k>32767||K>65535)return {};
  vector<int> vertices,codes;for(int gi=0;gi<k;gi++){vertices.push_back(groups[gi].front());codes.push_back(2*gi);if(groups[gi].size()>1){vertices.push_back(groups[gi].back());codes.push_back(2*gi+1);}}
  size_t P=vertices.size();auto unique=vertices;sort(unique.begin(),unique.end());if(adjacent_find(unique.begin(),unique.end())!=unique.end())return {};
  uint64_t pairs=uint64_t(P)*(P?P-1:0)/2,contextBytes=uint64_t(n)*3*sizeof(vector<int>)+uint64_t(K)*sizeof(vector<int>);
  for(auto&v:a)contextBytes+=v.capacity()*sizeof(int);for(auto&v:cw)contextBytes+=v.capacity()*sizeof(int);for(auto&v:w)contextBytes+=v.capacity()*sizeof(int);for(auto&v:bits)contextBytes+=v.capacity()*sizeof(uint64_t);
  if(pairs*6+contextBytes+(512ULL<<20)>(8ULL<<30))return {};
  enabled=true;vector<uint16_t> scores(pairs,0);vector<uint64_t> histogram(K+1),begin(K+1),cursor;
  auto index=[&](size_t i,size_t j){if(i>j)swap(i,j);return uint64_t(i)*(2*P-i-1)/2+(j-i-1);};
  for(size_t i=0;i<P;i++)for(size_t j=i+1;j<P;j++)if(codes[i]/2!=codes[j]/2){int z=co(vertices[i],vertices[j]);scores[index(i,j)]=uint16_t(z);if(z)histogram[z]++;}
  uint64_t total=0;for(int z=K;z>0;z--){begin[z]=total;total+=histogram[z];}cursor=begin;vector<uint32_t> edges(total);
  // Original point-pair construction orients each edge by original vertex ID.
  // Emit in (a,ea,b,eb) descending order into co-score buckets: exactly the
  // same lexicographic ordering as the reference tuple sort, with no edges dropped.
  for(int i=int(P)-1;i>=0;i--)for(int j=int(P)-1;j>=0;j--)if(vertices[i]<vertices[j]&&codes[i]/2!=codes[j]/2){int z=scores[index(i,j)];if(z)edges[cursor[z]++]=(uint32_t(codes[i])<<16)|uint32_t(codes[j]);}
  vector<uint16_t>().swap(scores);DS d(k);vector<int> seen(k),used(2*k);vector<vector<tuple<int,int,int>>> links(k);
  for(uint32_t edge:edges){int ap=edge>>16,bp=edge&65535,a=ap/2,ea=ap%2,b=bp/2,eb=bp%2;if(used[ap]||used[bp])continue;if((groups[a].size()==1&&!links[a].empty())||(groups[b].size()==1&&!links[b].empty()))continue;if(!d.u(a,b))continue;used[ap]=used[bp]=1;links[a].emplace_back(ea,b,eb);links[b].emplace_back(eb,a,ea);}
  vector<int>out;auto append=[&](int g,bool forward){if(forward)out.insert(out.end(),groups[g].begin(),groups[g].end());else out.insert(out.end(),groups[g].rbegin(),groups[g].rend());};
  for(int st=0;st<k;st++)if(!seen[st]&&links[st].size()!=2){bool fw=links[st].empty()||get<0>(links[st][0])==1;append(st,fw);seen[st]=1;int cur=st;
   while(true){int next=-1,eb=0;for(auto [ea,b,e]:links[cur])if(!seen[b]){next=b;eb=e;break;}if(next<0)break;append(next,eb==0);seen[next]=1;cur=next;}}
  for(int st=0;st<k;st++)if(!seen[st])append(st,true);return out;
 }
 vector<int> inter(const vector<vector<int>>&groups,bool dualSingleton){
  if(!dualSingleton){bool enabled=false;auto result=dense_inter(groups,enabled);if(enabled)return result;}
  int k=groups.size();vector<vector<pair<int,int>>>ports(n);vector<int>pts;
  for(int gi=0;gi<k;gi++){int x=groups[gi][0],y=groups[gi].back();ports[x].emplace_back(gi,0);pts.push_back(x);if(x!=y||dualSingleton){ports[y].emplace_back(gi,1);pts.push_back(y);}}
  // Pack (a,ea) and (b,eb). For a singleton on the b side, its two
  // candidates are consecutive in the exact lexicographic ordering, so
  // retain one record and visit eb=1,0 during consumption. No edge is dropped.
  vector<tuple<int,int,int>>cand;int64_t skips=0;
  pointpairs(pts,false,[&](int x,int y,int z){for(auto [a,ea]:ports[x]){
   if(ports[y].size()==2&&ports[y][0].first==ports[y][1].first){int b=ports[y][0].first;if(a!=b)cand.emplace_back(z,2*a+ea,4*b+3);}
   else for(auto [b,eb]:ports[y])if(a!=b)cand.emplace_back(z,2*a+ea,4*b+eb);
   if(cand.size()>200000000ULL)throw runtime_error("inter candidate workspace exceeds 8GiB safety budget; INCOMPLETE");}},skips);
  sort(cand.begin(),cand.end(),greater<>());DS d(k);vector<int>seen(k),used(2*k);vector<vector<tuple<int,int,int>>>links(k);
  for(auto [z,ap,bp]:cand){int a=ap/2,ea=ap%2,b=bp/4;for(int eb=(bp&2)?1:(bp&1);eb>=((bp&2)?0:(bp&1));eb--){if(used[2*a+ea]||used[2*b+eb])continue;if(!dualSingleton&&((groups[a].size()==1&&!links[a].empty())||(groups[b].size()==1&&!links[b].empty())))continue;if(!d.u(a,b))continue;used[2*a+ea]=used[2*b+eb]=1;links[a].emplace_back(ea,b,eb);links[b].emplace_back(eb,a,ea);}}
  vector<int>out;auto append=[&](int g,bool forward){if(forward)out.insert(out.end(),groups[g].begin(),groups[g].end());else out.insert(out.end(),groups[g].rbegin(),groups[g].rend());};
  for(int st=0;st<k;st++)if(!seen[st]&&links[st].size()!=2){bool fw=links[st].empty()||get<0>(links[st][0])==1;append(st,fw);seen[st]=1;int cur=st;
   while(true){int next=-1,eb=0;for(auto [ea,b,e]:links[cur])if(!seen[b]){next=b;eb=e;break;}if(next<0)break;append(next,eb==0);seen[next]=1;cur=next;}}
  for(int st=0;st<k;st++)if(!seen[st])append(st,true);return out;
 }
 vector<int> chain(const vector<int>&pts,int64_t&skips){
  vector<tuple<int,int,int>>cand;pointpairs(pts,true,[&](int x,int y,int c){cand.emplace_back(c,x,y);},skips);sort(cand.begin(),cand.end(),greater<>());DS d(n);vector<int>deg(n),seen(n);vector<vector<int>>nb(n);
  for(auto [c,x,y]:cand)if(deg[x]<2&&deg[y]<2&&d.u(x,y)){deg[x]++;deg[y]++;nb[x].push_back(y);nb[y].push_back(x);}
  vector<int>out;for(int s:pts)if(!seen[s]&&deg[s]!=2){int prev=-1,cur=s;while(cur!=-1){seen[cur]=1;out.push_back(cur);int next=-1;for(int x:nb[cur])if(x!=prev&&!seen[x]){next=x;break;}prev=cur;cur=next;}}for(int s:pts)if(!seen[s])out.push_back(s);return out;
 }
 vector<int> layout(const int32_t*pi,const int32_t*res,int nr,int rule,bool d,int64_t&skips){
  vector<int>D(res,res+nr);vector<char>isD(n);for(int v:D)isD[v]=1;auto groups=d?intra():w;vector<int>tail,korder;
  if(d){if(!groups.empty()&&groups.back().size()<size_t(W)){tail=groups.back();groups.pop_back();}if(rule==4){for(int v:D)groups.push_back({v});auto out=inter(groups,true);out.insert(out.end(),tail.begin(),tail.end());return out;}korder=inter(groups,false);korder.insert(korder.end(),tail.begin(),tail.end());}
  else for(auto&g:groups)korder.insert(korder.end(),g.begin(),g.end());
  if(rule==0){korder.insert(korder.end(),D.begin(),D.end());return korder;}
  if(rule==1){auto c=chain(D,skips);korder.insert(korder.end(),c.begin(),c.end());return korder;}
  if(rule==2){vector<int>out;int j=0;for(int i=0;i<n;i++)out.push_back(isD[pi[i]]?pi[i]:korder[j++]);return out;}
  if(rule==3){vector<int>winof(n,-1);for(int gi=0;gi<K;gi++)for(int v:w[gi])winof[v]=gi;vector<vector<int>>owner(K);int last=w[0][0];for(int i=0;i<n;i++){int v=pi[i];if(isD[v])owner[winof[last]].push_back(v);else last=v;}vector<int>out;int i=0;while(i<(int)korder.size()){int gi=winof[korder[i]],sz=w[gi].size();out.insert(out.end(),korder.begin()+i,korder.begin()+i+sz);out.insert(out.end(),owner[gi].begin(),owner[gi].end());i+=sz;}return out;}
  throw runtime_error("unknown rule");
 }
 void metrics(const int32_t*sigma,int64_t*out){
  vector<int>pos(n),at(n);for(int i=0;i<n;i++){pos[sigma[i]]=i;at[i]=sigma[i];}vector<int>mark(n,-1),bmark((n+W-1)/W,-1),Rs;int64_t U=0,T=0,R=0,G=0,WR=0;
  for(int wi=0;wi<K;wi++){vector<int>cols;for(int v:w[wi])for(int c:a[v])if(mark[c]!=wi){mark[c]=wi;cols.push_back(c);}U+=cols.size();T+=(cols.size()+15)/16;int r=0;
   for(int c:cols){int p=pos[c];r+=p==0||mark[at[p-1]]!=wi;int h=p/W;if(bmark[h]!=wi){bmark[h]=wi;G++;}}R+=r;Rs.push_back(r);
   vector<int>ps;for(int v:w[wi])ps.push_back(pos[v]);sort(ps.begin(),ps.end());for(size_t j=0;j<ps.size();j++)WR+=j==0||ps[j]!=ps[j-1]+1;
  }sort(Rs.begin(),Rs.end());out[0]=K;out[1]=U;out[2]=T;out[3]=G;out[4]=R;out[5]=K?Rs[min(K-1,int(.5*K))]:0;out[6]=K?Rs[min(K-1,int(.9*K))]:0;out[7]=K?Rs.back():0;out[8]=WR;
 }
};
extern "C"{
 void* lc_make(int n,const int64_t*p,const int32_t*c,const int32_t*flat,const int64_t*wp,int k,int W,int diag){return new Context(n,p,c,flat,wp,k,W,diag);}void lc_free(void*p){delete static_cast<Context*>(p);}
 int lc_layout(void*p,const int32_t*pi,const int32_t*D,int nr,int rule,int d,int32_t*out,int64_t*stats,char*err){try{auto&g=*static_cast<Context*>(p);int64_t skips=0;auto v=g.layout(pi,D,nr,rule,d,skips);if(v.size()!=size_t(g.n))throw runtime_error("layout length mismatch");copy(v.begin(),v.end(),out);stats[0]=skips;return 0;}catch(const exception&e){string s=e.what();copy_n(s.c_str(),min(size_t(1023),s.size()+1),err);return 1;}}
 void lc_metrics(void*p,const int32_t*sigma,int64_t*out){static_cast<Context*>(p)->metrics(sigma,out);}
}
