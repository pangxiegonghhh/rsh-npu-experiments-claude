#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>
struct Guard {uint64_t bytes;double started;char path[4096];};
static double now_seconds(void){struct timespec t;clock_gettime(CLOCK_REALTIME,&t);return t.tv_sec+t.tv_nsec/1e9;}
static void *watch(void *arg){struct Guard *g=(struct Guard*)arg;for(;;){struct rusage r;getrusage(RUSAGE_SELF,&r);uint64_t bytes=(uint64_t)r.ru_maxrss;
#ifndef __APPLE__
 bytes*=1024;
#endif
 if(bytes>g->bytes){FILE *f=fopen(g->path,"w");if(f){fprintf(f,"{\"status\":\"INCOMPLETE\",\"reason\":\"process resident-memory guard exceeded frozen limit; no truncated output accepted\",\"pid\":%d,\"limit_bytes\":%llu,\"peak_rss_bytes\":%llu,\"started_at\":%.9f,\"triggered_at\":%.9f,\"exitcode\":137}\n",getpid(),(unsigned long long)g->bytes,(unsigned long long)bytes,g->started,now_seconds());fclose(f);} _exit(137);}struct timespec pause={0,250000000};nanosleep(&pause,0);}return 0;}
int start_memory_guard(uint64_t bytes,const char *path){if(strlen(path)>=4096)return 1;struct Guard *g=malloc(sizeof(*g));if(!g)return 2;g->bytes=bytes;g->started=now_seconds();strcpy(g->path,path);pthread_t t;int rc=pthread_create(&t,0,watch,g);if(rc){free(g);return rc;}pthread_detach(t);return 0;}
