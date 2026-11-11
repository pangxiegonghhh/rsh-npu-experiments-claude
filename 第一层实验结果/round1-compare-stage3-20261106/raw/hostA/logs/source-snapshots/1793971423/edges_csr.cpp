#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <zlib.h>
using namespace std;
int main(int argc,char**argv){if(argc!=4)return 2;int n=atoi(argv[1]);string path=argv[2],out=argv[3];vector<int64_t>p(n+1);int64_t entries=0,diagonal=0;char line[128];
 for(int pass=0;pass<2;pass++){
  gzFile f=gzopen(path.c_str(),"rb");if(!f)return 3;vector<int64_t>at;static vector<int32_t>c;
  if(pass){c.resize(p[n]);at=p;}
  while(gzgets(f,line,sizeof(line))){char*end;long a=strtol(line,&end,10),b=strtol(end+1,&end,10);if(a<0||b<0||a>=n||b>=n)return 4;
   if(!pass){entries++;diagonal+=a==b;if(a!=b){p[a+1]++;p[b+1]++;}}
   else if(a!=b){c[at[a]++]=b;c[at[b]++]=a;}
  }int ze;gzerror(f,&ze);if(ze!=Z_OK&&ze!=Z_STREAM_END)return 5;gzclose(f);
  if(!pass){for(int i=0;i<n;i++)p[i+1]+=p[i];cerr<<"raw entries "<<entries<<" diagonal "<<diagonal<<" expanded "<<p[n]<<endl;}
  else{
   vector<int64_t>np(n+1);int64_t write=0;for(int r=0;r<n;r++){sort(c.begin()+p[r],c.begin()+p[r+1]);int last=-1;for(int64_t j=p[r];j<p[r+1];j++)if(c[j]!=last){last=c[j];c[write++]=last;}np[r+1]=write;}
   ofstream fp(out+"/indptr.raw",ios::binary);fp.write((char*)np.data(),np.size()*8);ofstream fc(out+"/indices.raw",ios::binary);fc.write((char*)c.data(),write*4);ofstream meta(out+"/edge-parser.json");meta<<"{\"n\":"<<n<<",\"stored_entries\":"<<entries<<",\"diagonal_entries\":"<<diagonal<<",\"nnz_A0\":"<<write<<",\"explicit_zero_entries\":0,\"source_type\":\"unweighted edge CSV\"}\n";
  }
 }return 0;}
