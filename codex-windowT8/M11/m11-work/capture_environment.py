from pathlib import Path
import subprocess,os,platform,json,hashlib,shutil,time
root=Path(__file__).resolve().parent;out=root/'environment';out.mkdir(exist_ok=True)
commands={'npu-smi':['npu-smi','info'],'chip':['npu-smi','info','-t','board','-i','1'],'processes':['ps','-eo','pid,comm,args'],'compiler':['c++','--version'],'clock':['date','-u'],'memory':['free','-h']}
for name,cmd in commands.items():
 r=subprocess.run(cmd,capture_output=True,text=True);(out/(name+'.txt')).write_text(r.stdout+r.stderr)
home=Path(os.environ['ASCEND_HOME_PATH']);(out/'environment.json').write_text(json.dumps(dict(ASCEND_HOME_PATH=str(home),machine=platform.machine(),container=platform.node(),epoch=time.time()),indent=2))
for pattern in ['kernel_struct_data_copy.h','kernel_struct_data_copy_v2.h','kernel_struct_mm.h']:
 for file in home.rglob(pattern):
  if 'aarch64-linux/asc/include/basic_api/' in str(file):shutil.copyfile(file,out/file.name)
(out/'file-sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2))
print('M11_ENV_SAVED',flush=True)
