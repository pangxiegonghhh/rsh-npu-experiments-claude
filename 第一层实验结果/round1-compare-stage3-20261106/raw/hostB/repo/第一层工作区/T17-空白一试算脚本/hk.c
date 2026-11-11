// Max-weight Hamiltonian path (free endpoints) on s<=16 nodes, Held-Karp.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(){
  int B; if(scanf("%d",&B)!=1) return 1;
  static int dp[1<<16][16]; static signed char par[1<<16][16];
  for(int b=0;b<B;b++){
    int s; if(scanf("%d",&s)!=1) return 1; int w[16][16];
    for(int i=0;i<s;i++)for(int j=0;j<s;j++) if(scanf("%d",&w[i][j])!=1) return 1;
    int F=1<<s;
    for(int m=0;m<F;m++)for(int i=0;i<s;i++){dp[m][i]=-1;par[m][i]=-1;}
    for(int i=0;i<s;i++)dp[1<<i][i]=0;
    for(int m=1;m<F;m++)for(int i=0;i<s;i++){ if(dp[m][i]<0)continue; if(!(m>>i&1))continue;
      for(int j=0;j<s;j++){ if(m>>j&1)continue; int nm=m|1<<j; int v=dp[m][i]+w[i][j];
        if(v>dp[nm][j]){dp[nm][j]=v;par[nm][j]=i;} } }
    int best=-1,bl=0; for(int i=0;i<s;i++) if(dp[F-1][i]>best){best=dp[F-1][i];bl=i;}
    int ord[16]; int m=F-1,cur=bl; for(int t=s-1;t>=0;t--){ord[t]=cur; int p=par[m][cur]; m&=~(1<<cur); cur=p;}
    printf("%d",best); for(int t=0;t<s;t++)printf(" %d",ord[t]); printf("\n");
  }
  return 0;
}
