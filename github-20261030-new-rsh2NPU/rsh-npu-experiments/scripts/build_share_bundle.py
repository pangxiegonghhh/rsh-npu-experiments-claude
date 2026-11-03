"""Build a portable local reading/recovery bundle; never starts NPU tasks."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / '对外资料' / 'RSH-910B-资料包-20261020'
ZIP = DEST.with_suffix('.zip')
resume = sys.argv[1:] == ['--resume']
if ZIP.exists() or (DEST.exists() and not resume):
    raise SystemExit('Target already exists; preserving the existing share bundle.')
if resume and not (DEST / ROOT.name / '项目资料总览.md').is_file():
    raise SystemExit('Expected prepared share directory is missing.')
DEST.mkdir(parents=True, exist_ok=True)
project = DEST / ROOT.name
project.mkdir(exist_ok=True)
ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '.mpl-cache', '.DS_Store')
for name in ['results', 'inputs', 'scripts', 'npu', 'rsh', 'diagnostics', 'docs', 'tests']:
    if not resume:
        shutil.copytree(ROOT / name, project / name, ignore=ignore)
for p in ROOT.iterdir():
    if p.is_file() and (p.suffix == '.md' or p.name == 'requirements.txt'):
        shutil.copy2(p, project / p.name)

literature = ROOT.parent / 'idea-sop'
note_dir = Path('runs/2026-10-16-rsh-ascend-assessment')
if not resume:
    shutil.copytree(literature / note_dir, DEST / 'idea-sop' / note_dir, ignore=ignore)
for name in ['P010-RSH-SpMM.pdf', 'P006-NeutronSparse.pdf']:
    target = DEST / 'idea-sop/pdfs' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(literature / 'pdfs' / name, target)

backups = [
    'rsh-910b-recovery-through-d3-20261019.tar.gz',
    'rsh-910b-d3-closeout-20261019.tar.gz',
    'rsh-910b-next-plan-after-d3-20261019.tar.gz',
    'rsh-910b-design-roadmap-20261019.tar.gz',
    'rsh-910b-project-overview-20261020.tar.gz',
]
target_backup = project / 'artifacts/backups'
target_backup.mkdir(parents=True, exist_ok=True)
for name in backups:
    for tail in ['', '.sha256']:
        shutil.copy2(ROOT / 'artifacts/backups' / (name + tail), target_backup / (name + tail))

(DEST / '从这里开始.md').write_text('''# RSH → 910B 研究资料包

整理日期：2026-10-20。先将整个压缩包解压，再从本文件进入。

1. [项目资料总览](rsh-spmm-910b/项目资料总览.md)：研究目标、文献、各轮设计/结果、当前路线与资料位置。
2. [实验数据速查](rsh-spmm-910b/docs/project-overview-20261020/实验数据速查.md)：D3全部24点及阶段规模。
3. [整体路线与Cube供数主线](rsh-spmm-910b/docs/npu-design-roadmap-20261019/整体路线与Cube供数主线.md)：当前讨论入口；旧D4–D6暂缓。

请保持 rsh-spmm-910b 与 idea-sop 两个文件夹处于同一级，保留内部目录结构。使用支持相对链接的Markdown阅读器打开；不要仅转发某一篇md，也不要在压缩包预览中直接点击链接。

## 包含的资料

- 原有研究总览、设计、报告、图表和原始results记录。
- 保存的inputs、规划/算子/诊断/审计代码及测试源码。
- 与总览关联的文献核查笔记及RSH/NeutronSparse两篇论文。
- 最新D3完整恢复包及后续文档补充包，附SHA256。展开的重复cases/build中间目录未再次复制；正式复现实验请先参阅[恢复环境](rsh-spmm-910b/恢复环境.md)，按恢复链准备新环境。

历史备份清单还记载较早阶段的独立备份，其中未选入本包的旧归档仍可在最新完整恢复包覆盖的状态中追溯；本包不是当前工作目录13GB的逐字节镜像。报告和旧日志中的机器绝对路径属于历史记录；阅读入口使用相对路径。未实施新设备实验，也未执行任何发送操作。

## 使用边界

数据是固定矩阵结构与当前实现上的受控实验；完整应用成本、强稀疏库竞争力、新机制新颖性仍未完成验证。解压或阅读不会启动实验；run/sequence脚本可能执行设备任务，应按阶段协议使用。
''')

# Convert machine-absolute Markdown links only in the share copies.
rewritten = []
for p in DEST.rglob('*.md'):
    def portable(match):
        target = match.group(2).strip('<>')
        original = Path(target)
        if original.is_absolute() and original.is_relative_to(ROOT.parent):
            new = DEST / original.relative_to(ROOT.parent)
            if new.exists():
                rewritten.append({'document': str(p.relative_to(DEST)), 'old_target': target})
                return match.group(1) + os.path.relpath(new, p.parent) + match.group(3)
        return match.group(0)
    old = p.read_text(errors='replace')
    new = re.sub(r'(!?\[[^\]]*\]\()([^)]*)(\))', portable, old)
    if new != old:
        p.write_text(new)

# Follow relative Markdown links in the included corpus. Add only directly referenced
# literature files if an existing note points outside the initially selected subset.
added = []
for _ in range(12):
    growth = False
    for p in list(DEST.rglob('*.md')):
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', p.read_text(errors='replace')):
            target = target.strip('<>').split('#')[0]
            if not target or re.match(r'^[A-Za-z]+:', target):
                continue
            q = (p.parent / target).resolve()
            if q.exists():
                continue
            if not q.is_relative_to(DEST):
                raise RuntimeError('Link leaves portable root: ' + str(p) + ': ' + target)
            rel = q.relative_to(DEST)
            if rel.parts[0] == 'idea-sop':
                source = ROOT.parent / rel
                if source.is_file():
                    q.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, q)
                    added.append(str(rel))
                    growth = True
    if not growth:
        break

missing = []
links = 0
md_count = 0
for p in DEST.rglob('*.md'):
    md_count += 1
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', p.read_text(errors='replace')):
        target = target.strip('<>').split('#')[0]
        if not target or re.match(r'^[A-Za-z]+:', target):
            continue
        links += 1
        q = (p.parent / target).resolve()
        if not q.is_relative_to(DEST) or not q.exists():
            missing.append({'document': str(p.relative_to(DEST)), 'target': target})
if missing:
    (DEST / '链接待处理.json').write_text(json.dumps(missing, ensure_ascii=False, indent=2))
    raise RuntimeError(f'{len(missing)} local links require repair before release.')
pending = DEST / '链接待处理.json'
if pending.exists():
    pending.unlink()

files = sorted(p for p in DEST.rglob('*') if p.is_file())
hashes = {str(p.relative_to(DEST)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
manifest = {'date': '2026-10-20', 'local_markdown_files': md_count,
            'verified_local_links': links, 'broken_local_links': 0,
            'additional_referenced_literature': added, 'files': hashes,
            'machine_absolute_links_rewritten_in_copies': rewritten,
            'device_experiment_started': False}
(DEST / '资料包清单.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'directory_ready', 'directory': str(DEST), 'files': len(files)+1,
                  'markdown_files': md_count, 'local_links_verified': links}, ensure_ascii=False), flush=True)
with zipfile.ZipFile(ZIP, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=4, allowZip64=True) as z:
    for p in sorted(DEST.rglob('*')):
        if p.is_file():
            store = p.name.endswith(('.tar.gz', '.npz', '.png', '.pdf', '.gz'))
            z.write(p, str(p.relative_to(DEST.parent)), compress_type=zipfile.ZIP_STORED if store else zipfile.ZIP_DEFLATED)
print(json.dumps({'status': 'zip_written', 'archive': str(ZIP), 'bytes': ZIP.stat().st_size}, ensure_ascii=False), flush=True)
with zipfile.ZipFile(ZIP) as z:
    assert z.testzip() is None
    assert len(z.infolist()) == len(hashes) + 1
sha = hashlib.sha256(ZIP.read_bytes()).hexdigest()
Path(str(ZIP) + '.sha256').write_text(sha + '  ' + ZIP.name + '\n')
report = {'passed': True, 'directory': str(DEST), 'archive': str(ZIP),
          'archive_bytes': ZIP.stat().st_size, 'sha256': sha,
          'files': len(hashes)+1, 'markdown_files': md_count,
          'verified_local_links': links, 'broken_local_links': 0,
          'zip_crc_passed': True, 'device_experiment_started': False}
(ROOT / 'results/share_bundle_verification_20261020.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False), flush=True)
