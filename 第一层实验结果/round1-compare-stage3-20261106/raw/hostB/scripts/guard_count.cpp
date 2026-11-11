#include <cstdint>
#include <vector>
extern "C" int64_t count_guard_windows(int n,const int64_t*p,const int32_t*c,const int32_t*flat,const int64_t*wp,int k,const int32_t*res,int nr,int threshold){
 std::vector<unsigned char> is_res(n,0);std::vector<int> seen(n,-1);
 for(int i=0;i<nr;i++)is_res[res[i]]=1;
 int64_t skipped=0;
 for(int wi=0;wi<k;wi++){
  int count=0;bool over=false;
  for(int64_t j=wp[wi];j<wp[wi+1]&&!over;j++){
   int r=flat[j];
   for(int64_t q=p[r];q<p[r+1];q++){
    int v=c[q];if(is_res[v]&&seen[v]!=wi){seen[v]=wi;if(++count>threshold){over=true;break;}}
   }
  }
  skipped+=over;
 }
 return skipped;
}
