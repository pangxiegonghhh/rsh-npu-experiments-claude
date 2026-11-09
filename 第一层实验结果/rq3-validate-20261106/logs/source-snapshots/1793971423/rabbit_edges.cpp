#include <cstdint>
#include <zlib.h>
extern "C" int rabbit_edges(int n,const int64_t*p,const int32_t*c,int bipartite,const char*path){gzFile f=gzopen(path,"wb1");if(!f)return 1;for(int r=0;r<n;r++)for(int64_t j=p[r];j<p[r+1];j++)if(bipartite||r<c[j])gzprintf(f,"%d %d\n",r,bipartite?n+c[j]:c[j]);return gzclose(f)==Z_OK?0:2;}
