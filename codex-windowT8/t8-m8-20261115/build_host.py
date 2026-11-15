from pathlib import Path
p=Path(__file__).resolve().parent
prefix=(p.parent/'t8-m4-20261114/host.cpp').read_text().split('struct Run{')[0]
prefix=prefix.replace('#include <cmath>','#include <cmath>\n#include <iomanip>')
prefix=prefix.replace('extern "C" void t8_launch(void*,void*,void*,void*,void*,void*,void*,void*,void*,uint32_t);','extern "C" void t8_launch(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,uint32_t);')
prefix=prefix.replace('float value=1+(m*3+k*5)%7;', 'float value=m==k?1.0f:0.0f;')
prefix=prefix.replace('std::memcpy((char*)raw.data()+index*2,&h,2);','std::memcpy((char*)raw.data()+index*2,&h,2);')
# h16 handles zero explicitly for the identity matrix.
prefix=prefix.replace('uint16_t h16(float v){','uint16_t h16(float v){if(v==0)return 0;')
prefix=prefix.replace('struct C4{', 'struct C4{')
prefix=prefix.replace('}a.put(raw.data());','}a.put(raw.data());')
# Reserve the final row as a genuine immutable zero row, and audit it separately.
prefix=prefix.replace('v[r*n+j]=bv(r,j);','v[r*n+j]=r+1==rows?0:bv(r,j);')
prefix=prefix.replace('v[r*n+j]=h16(bv(r,j));','v[r*n+j]=h16(r+1==rows?0:bv(r,j));')
prefix=prefix.replace('auto want=bv(logical/n,logical%n);','auto want=logical/n+1==b.bytes/(n*es)?0:bv(logical/n,logical%n);')
(p/'host.cpp').write_text(prefix+(p/'host-body.cpp').read_text())
print('host generated')
