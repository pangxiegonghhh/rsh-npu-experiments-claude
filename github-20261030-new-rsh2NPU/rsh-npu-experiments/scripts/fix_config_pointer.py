"""Compatibility repair for the CANN 9 legacy generated launch headers."""
from pathlib import Path

root=Path(__file__).resolve().parents[1]
p=root/'npu/kernels.cpp'
s=p.read_text()
marker='#define ALL_ARGS '
load='''__aicore__ inline RshConfig LoadConfig(GM_ADDR config) {
    GlobalTensor<int32_t> x;x.SetGlobalBuffer((__gm__ int32_t*)config);
    RshConfig c;
    c.m=x.GetValue(0);c.k=x.GetValue(1);c.n=x.GetValue(2);c.stride=x.GetValue(3);
    c.nnz=x.GetValue(4);c.groups=x.GetValue(5);c.blocks=x.GetValue(6);
    c.sparseRows=x.GetValue(7);c.cores=x.GetValue(8);return c;
}

'''
assert 'LoadConfig' not in s
s=s.replace(marker,load+marker,1)
s=s.replace('GM_ADDR output,const RshConfig c','GM_ADDR output,GM_ADDR config')
s=s.replace('rows,rhs,packed,output,c\n','rows,rhs,packed,output,config\n')
for kind in ('AIC_ONLY','AIV_ONLY','MIX_AIC_1_2'):
    line=f'    KERNEL_TASK_TYPE_DEFAULT(KERNEL_TYPE_{kind});\n'
    s=s.replace(line,line+'    RshConfig c=LoadConfig(config);\n')
s=s.replace('void* packed,void* output,void* map) {','void* packed,void* output,void* map,void* config) {')
s=s.replace('(GM_ADDR)output,c);','(GM_ADDR)output,(GM_ADDR)config);')
p.write_text(s)
p=root/'npu/runner.cpp';s=p.read_text()
s=s.replace('void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);','void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*);')
s=s.replace('packed,out,map;','packed,out,map,config;')
s=s.replace('  auto t=Clock::now();','  config=std::make_unique<Buffer>(sizeof(c));check(aclrtMemcpy(config->device,config->size,&c,sizeof(c),ACL_MEMCPY_HOST_TO_DEVICE));\n  auto t=Clock::now();',1)
s=s.replace('out->device,map->device);','out->device,map->device,config->device);')
p.write_text(s)
print('Changed device entrypoints to pointer-based config.')
