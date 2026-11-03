#include "common.h"
#include <cstdlib>
extern "C" void rsh_launch_cube(void*,int,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);
extern "C" void rsh_launch_cube_e0_direct(void*,int,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);
extern "C" void rsh_launch_vector(void*,int,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);
extern "C" void rsh_launch_mix(void*,int,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);
extern "C" void rsh_launch_restore(void*,int,void*,void*,void*,void*);
extern "C" void rsh_launch(void* stream,int kind,const RshConfig c,
 void* ptr,void* cols,void* vals,void* gp,void* refs,void* tiles,void* rows,void* rhs,void* packed,void* output,void* map,void* config) {
    if(kind==0)rsh_launch_vector(stream,c.cores*2,ptr,cols,vals,gp,refs,tiles,rows,rhs,packed,output,config);
    else if(kind==1) {
        const char* direct=std::getenv("RSH_E0_DIRECT_A");
        if(direct && direct[0]=='1')rsh_launch_cube_e0_direct(stream,c.cores,ptr,cols,vals,gp,refs,tiles,rows,rhs,packed,output,config);
        else rsh_launch_cube(stream,c.cores,ptr,cols,vals,gp,refs,tiles,rows,rhs,packed,output,config);
    }
    else rsh_launch_mix(stream,c.cores,ptr,cols,vals,gp,refs,tiles,rows,rhs,packed,output,config);
    if(c.groups)rsh_launch_restore(stream,c.cores*2,packed,map,output,config);
}
