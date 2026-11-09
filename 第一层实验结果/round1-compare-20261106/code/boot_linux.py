import json,os,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
cmd=[str(BASE/'work/qemu-launch'),str(BASE/'work/utm-mount/UTM.app/Contents/Frameworks/qemu-aarch64-softmmu.framework/Versions/A/qemu-aarch64-softmmu'),'-machine','virt','-accel','hvf','-cpu','host','-m','4096','-smp','2','-nographic','-kernel',str(BASE/'deps/alpine/vmlinuz-virt'),'-initrd',str(BASE/'deps/alpine/initramfs-virt'),'-append','console=ttyAMA0 alpine_repo=https://dl-cdn.alpinelinux.org/alpine/v3.22/main modloop=https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/aarch64/netboot/modloop-virt modules=loop,squashfs,sd-mod,virtio_net ip=dhcp','-netdev','user,id=net0,hostfwd=tcp:127.0.0.1:22221-:22','-device','virtio-net-device,netdev=net0']
(BASE/'logs/linux-boot-command.json').write_text(json.dumps(dict(command=cmd,start=time.time()),indent=2))
p=subprocess.Popen(cmd,stdin=sys.stdin,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
with (BASE/'logs/linux-console.raw').open('ab',buffering=0) as log:
 while True:
  b=os.read(p.stdout.fileno(),65536)
  if not b:break
  log.write(b);os.write(sys.stdout.fileno(),b)
raise SystemExit(p.wait())
