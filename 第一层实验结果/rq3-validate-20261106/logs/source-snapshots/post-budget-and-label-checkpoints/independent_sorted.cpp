// Independent metric checker: concatenate positions, sort/unique and count runs.
// No candidate, placement, or Layout implementation is linked or imported.
#include <algorithm>
#include <cstdint>
#include <vector>
extern "C" void independent_sorted(int n,const int64_t*p,const int32_t*c,const int32_t*flat,const int64_t*gp,int k,const int32_t*sigma,int W,int diagonal,int64_t*out){
 std::vector<int> inverse(n),runs;for(int i=0;i<n;i++)inverse[sigma[i]]=i;
 int64_t U=0,T=0,G=0,R=0,wr=0;
 for(int wi=0;wi<k;wi++){
  std::vector<int> positions,rowpos;
  for(int64_t t=gp[wi];t<gp[wi+1];t++){
   int r=flat[t];rowpos.push_back(inverse[r]);for(int64_t j=p[r];j<p[r+1];j++)positions.push_back(inverse[c[j]]);if(diagonal)positions.push_back(inverse[r]);
  }
  std::sort(positions.begin(),positions.end());positions.erase(std::unique(positions.begin(),positions.end()),positions.end());U+=positions.size();T+=(positions.size()+15)/16;
  int nr=0,ng=0;for(size_t i=0;i<positions.size();i++){nr+=i==0||positions[i]!=positions[i-1]+1;ng+=i==0||positions[i]/W!=positions[i-1]/W;}R+=nr;G+=ng;runs.push_back(nr);
  std::sort(rowpos.begin(),rowpos.end());for(size_t i=0;i<rowpos.size();i++)wr+=i==0||rowpos[i]!=rowpos[i-1]+1;
 }
 std::sort(runs.begin(),runs.end());int64_t values[]={k,U,T,G,R,k?runs[std::min(k-1,k/2)]:0,k?runs[std::min(k-1,int(.9*k))]:0,k?runs.back():0,wr};std::copy(values,values+9,out);
}
