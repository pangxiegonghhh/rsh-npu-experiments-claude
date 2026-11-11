import ctypes as C,os,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
_path=None
_library=None
def ensure_limit(limit=8*2**30):
 global _path,_library
 if _path is not None:return _path
 root=BASE/'logs/memory-guards';root.mkdir(exist_ok=True);path=root/f'{os.getpid()}-{time.time_ns()}.json';_library=C.CDLL(str(BASE/'work/libmemory-guard.dylib'));_library.start_memory_guard.argtypes=[C.c_uint64,C.c_char_p];_library.start_memory_guard.restype=C.c_int;assert _library.start_memory_guard(limit,str(path).encode())==0;_path=str(path);return _path
