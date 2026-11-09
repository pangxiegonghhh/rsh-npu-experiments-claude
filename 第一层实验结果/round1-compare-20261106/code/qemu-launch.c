#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char**argv,char**envp){
 if(argc<2)return 2;
 void*p=dlopen(argv[1],RTLD_LOCAL|RTLD_LAZY|RTLD_FIRST);if(!p){fprintf(stderr,"%s\n",dlerror());return 3;}
 void(*init)(int,char**,char**)=dlsym(p,"qemu_init");void(*loop)(void)=dlsym(p,"qemu_main_loop");void(*cleanup)(void)=dlsym(p,"qemu_cleanup");
 if(!init||!loop||!cleanup){fprintf(stderr,"QEMU interface unavailable\n");return 4;}init(argc-1,argv+1,envp);loop();cleanup();return 0;
}
