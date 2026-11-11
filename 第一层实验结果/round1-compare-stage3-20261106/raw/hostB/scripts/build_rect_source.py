from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
s=(BASE/'scripts/t21/accelerate-v8.cpp').read_text().split('#include <cstdlib>')[0]
start=s.index(' int n;');end=s.index(' double sim')
s=s[:start]+''' int n,nc;vector<vector<int>> a,s,inv;vector<int> deg,orig,id;
 Graph(int nc_,const int64_t*p,const int32_t*c,int nr,const int32_t*K):n(nr),nc(nc_),a(n),s(n),inv(nc),deg(n),orig(K,K+nr),id(nc,-1){
  for(int v=0;v<n;v++){id[orig[v]]=v;a[v].assign(c+p[orig[v]],c+p[orig[v]+1]);s[v]=a[v];sort(s[v].begin(),s[v].end());deg[v]=a[v].size();for(int x:a[v])inv[x].push_back(v);}
 }
'''+s[end:]
s=s.replace('vector<vector<int>> cols=s,rows=s;','vector<vector<int>> cols=s,rows=inv;')
s=s.replace('for(auto& x:cols)sort(x.begin(),x.end(),cmp);','for(auto& x:cols)sort(x.begin(),x.end(),[&](int c,int d){return inv[c].size()!=inv[d].size()?inv[c].size()>inv[d].size():c<d;});')
s=s.replace('colseen(n)','colseen(nc)').replace('for(int u:a[c])','for(int u:inv[c])')
start=s.index(' vector<int> gorder(');end=s.index(' void bp_split',start)
s=s[:start]+''' vector<int> gorder(int W,double beta)const{
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
'''+s[end:]
s=s.replace('vector<vector<int>> cnt(2,vector<int>(n))','vector<vector<int>> cnt(2,vector<int>(nc))')
s+='''
extern "C"{
 void* rect_make(int nc,const int64_t*p,const int32_t*c,int nr,const int32_t*K){return new Graph(nc,p,c,nr,K);}void rect_free(void*p){delete static_cast<Graph*>(p);}
 void rect_order(void*p,int method,int W,int32_t*out){auto*g=static_cast<Graph*>(p);vector<int>v;if(method==0||method==1)v=g->gorder(W,method==0);else if(method==2)v=g->rsh();else if(method==3)v=g->rabbit();else v=g->neutron(W);copy(v.begin(),v.end(),out);}
 void rect_bp(void*p,const int32_t*v,int size,int s1,int iters,const double*L,int32_t*out){static_cast<Graph*>(p)->bp_split(v,size,s1,iters,L,out);}
}
'''
(BASE/'scripts/rect.cpp').write_text(s)
