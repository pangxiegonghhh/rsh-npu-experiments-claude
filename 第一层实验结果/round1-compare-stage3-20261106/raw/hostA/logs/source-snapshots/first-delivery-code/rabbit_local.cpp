#include <algorithm>
#include <cstdint>
#include <vector>
using namespace std;
extern "C" void rabbit_local(int n,const int64_t*p,const int32_t*c,const int32_t*coarse,int nr,int W,int cn,int32_t*out){vector<vector<int>>a(n);for(int r=0;r<n;r++){a[r].assign(c+p[r],c+p[r+1]);sort(a[r].begin(),a[r].end());}auto inter=[&](int r,int s){size_t i=0,j=0;int z=0;while(i<a[r].size()&&j<a[s].size()){if(a[r][i]==a[s][j]){z++;i++;j++;}else if(a[r][i]<a[s][j])i++;else j++;}return z;};int write=0;
 for(int start=0;start<nr;start+=8*W){vector<int>rem(coarse+start,coarse+min(nr,start+8*W));while(!rem.empty()){int anchor=rem[0],cur=anchor;rem.erase(rem.begin());out[write++]=anchor;for(int k=1;k<W&&!rem.empty();k++){int best=0,bnum=-1,bden=1;for(int j=0;j<(int)rem.size();j++){int ref=cn?cur:anchor,z=inter(ref,rem[j]);int den=cn?1:a[ref].size()+a[rem[j]].size()-z;if(bnum<0||int64_t(z)*bden>int64_t(bnum)*den){best=j;bnum=z;bden=den;}}cur=rem[best];out[write++]=cur;rem.erase(rem.begin()+best);}}}
 for(int r=0;r<n;r++)if(p[r]==p[r+1])out[write++]=r;
}
