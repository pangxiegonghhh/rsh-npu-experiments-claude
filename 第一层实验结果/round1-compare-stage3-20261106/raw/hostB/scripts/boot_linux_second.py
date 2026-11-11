import json,os,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];disk=BASE/'work/linux-second-scratch.raw'
if not disk.exists():
 with disk.open('wb') as f:f.truncate(12*2**30)
qemu=BASE/'work/utm-mount/UTM.app/Contents/Frameworks/qemu-aarch64-softmmu.framework/Versions/A/qemu-aarch64-softmmu'
cmd=[str(BASE/'work/qemu-launch'),str(qemu),'-machine','virt','-accel','hvf','-cpu','host','-m','8192','-smp','2','-nographic','-kernel',str(BASE/'deps/alpine/vmlinuz-virt'),'-initrd',str(BASE/'deps/alpine/initramfs-virt'),'-append','console=ttyAMA0 alpine_repo=https://dl-cdn.alpinelinux.org/alpine/v3.22/main modloop=https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/aarch64/netboot/modloop-virt modules=loop,squashfs,sd-mod,virtio_net,virtio_blk ip=dhcp','-drive',f'file={disk},if=none,id=scratch,format=raw','-device','virtio-blk-device,drive=scratch','-netdev','user,id=net0,hostfwd=tcp:127.0.0.1:22221-:22','-device','virtio-net-device,netdev=net0']
(BASE/'logs/linux-second-boot-command.json').write_text(json.dumps(dict(command=cmd,start=time.time(),CPU_only=True,guest_memory_bytes=8*2**30,scratch='new local disposable sparse12GiB data disk',source='official Alpine3.22 and recovered verified author Rabbit binary'),indent=2));p=subprocess.Popen(cmd,stdin=sys.stdin,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
with (BASE/'logs/linux-second-console.raw').open('ab',buffering=0) as log:
 while True:
  data=os.read(p.stdout.fileno(),65536)
  if not data:break
  log.write(data);os.write(sys.stdout.fileno(),data)
raise SystemExit(p.wait())
