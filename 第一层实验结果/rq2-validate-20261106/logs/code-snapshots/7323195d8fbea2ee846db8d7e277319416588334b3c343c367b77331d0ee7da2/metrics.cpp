#include <algorithm>
#include <cstdint>
#include <vector>
using namespace std;
extern "C" int rq_metrics(int n,const int64_t*ptr,const int32_t*idx,const int32_t*order,int W,int tau,int inplace,int diag1,const int32_t*columns,int has_columns,int64_t*out){
 vector<int> kept,resid,pos(n),stamp(n,-1),blockstamp((n+W-1)/W,-1),rs,points;
 for(int i=0;i<n;i++){int v=order[i];(tau<0||ptr[v+1]-ptr[v]>tau?kept:resid).push_back(v);}
 if(has_columns)for(int i=0;i<n;i++)pos[columns[i]]=i;
 else if(tau<0||inplace)for(int i=0;i<n;i++)pos[order[i]]=i;
 else{int i=0;for(int v:kept)pos[v]=i++;for(int v:resid)pos[v]=i++;}
 int64_t U=0,T=0,G=0,R=0;int win=0;
 for(int start=0;start<(int)kept.size();start+=W,win++){
  points.clear();auto add=[&](int col){int p=pos[col];if(stamp[p]!=win){stamp[p]=win;points.push_back(p);}};
  for(int i=start;i<min((int)kept.size(),start+W);i++){int v=kept[i];for(int64_t j=ptr[v];j<ptr[v+1];j++)add(idx[j]);if(diag1)add(v);}
  int r=0,g=0;for(int p:points){r+=p==0||stamp[p-1]!=win;int b=p/W;if(blockstamp[b]!=win){blockstamp[b]=win;g++;}}
  int u=points.size();U+=u;T+=(u+15)/16;G+=g;R+=r;rs.push_back(r);
 }
 sort(rs.begin(),rs.end());int k=rs.size();out[0]=n;out[1]=k;out[2]=resid.size();out[3]=U;out[4]=T;out[5]=G;out[6]=R;out[7]=k?rs[min(k-1,int(.5*k))]:0;out[8]=k?rs[min(k-1,int(.9*k))]:0;out[9]=k?rs.back():0;out[10]=R-G;return 0;
}
