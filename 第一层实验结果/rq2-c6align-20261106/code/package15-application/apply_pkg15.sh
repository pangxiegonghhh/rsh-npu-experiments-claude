#!/bin/bash
# Package 15 (RSH-NPU): apply pkg15-0001.patch with hash checks. Never pushes.
# usage:  bash apply_pkg15.sh [path-to-repo]     (default: the git repo containing the current directory)
# Safe to run more than once: an already-applied state is recognised and only re-verified.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PATCH="$HERE/pkg15-0001.patch"
PATCH_SHA=96f44d14d05c404fc4410e04e68da0fc0c74d18ea853fba54b40f97e6b6e4aae
BEFORE_TREE=ff969ff7806c3eb5cdf0b1abbf954011b63ff95f
AFTER_TREE=ca3af5408b13a8ec9a424452649ebe943a902d19
NEW_DIR="第一层工作区/T21补跑-C6对齐修补"
NEW_NOTE="讨论记录/2026-11-06/2026-11-06-0922-C6对齐修补与T21补跑.md"

sha() { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi; }
die() { echo "STOP: $*" >&2; echo "Nothing was pushed." >&2; exit 1; }
check_list() {  # $1 = hash list file; prints mismatches; returns 0 only if every file matches
  local bad=0 line h f
  while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue
    h="${line%%  *}"; f="${line#*  }"
    if [ ! -f "$f" ]; then echo "    missing : $f"; bad=1
    elif [ "$(sha "$f")" != "$h" ]; then echo "    differs : $f"; bad=1; fi
  done < "$1"
  return $bad
}

echo "[1/6] patch hash"
[ -f "$PATCH" ] || die "pkg15-0001.patch not found next to this script"
[ "$(sha "$PATCH")" = "$PATCH_SHA" ] || die "pkg15-0001.patch hash differs from $PATCH_SHA (file damaged?)"
echo "      OK $PATCH_SHA"

echo "[2/6] repository"
REPO="${1:-}"
if [ -z "$REPO" ]; then REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository; pass the repo path as the first argument"; fi
cd "$REPO" || die "cannot cd to $REPO"
git rev-parse --git-dir >/dev/null 2>&1 || die "$REPO is not a git repository"
echo "      $(pwd)"
echo "      origin: $(git remote get-url origin 2>/dev/null || echo '(none)')"
GITDIR="$(git rev-parse --git-dir)"
[ -d "$GITDIR/rebase-apply" ] && die "a previous 'git am' is still in progress ($GITDIR/rebase-apply). Inspect it, then run 'git am --abort' yourself."

echo "[3/6] keep agent download area out of git (.git/info/exclude, .gitignore untouched)"
EXCL="$GITDIR/info/exclude"; mkdir -p "$GITDIR/info"; touch "$EXCL"
grep -qxF '/第一层工作区/agent下载文件区/' "$EXCL" || echo '/第一层工作区/agent下载文件区/' >> "$EXCL"
echo "      OK"

echo "[4/6] starting state"
TREE="$(git rev-parse 'HEAD^{tree}')"
echo "      HEAD $(git rev-parse HEAD)  tree $TREE"
MODE=""
if [ "$TREE" = "$AFTER_TREE" ]; then MODE=already
elif [ "$TREE" = "$BEFORE_TREE" ]; then MODE=apply_exact
elif check_list "$HERE/pkg15-sha256-after.txt" >/dev/null; then MODE=already_other
elif check_list "$HERE/pkg15-sha256-before.txt" >/dev/null; then MODE=apply_other
else
  echo "      neither the before- nor the after-state of package 15 matches:"
  echo "      before:"; check_list "$HERE/pkg15-sha256-before.txt"
  echo "      after:";  check_list "$HERE/pkg15-sha256-after.txt"
  die "unexpected starting state"
fi
echo "      mode: $MODE"

if [ "$MODE" = apply_exact ] || [ "$MODE" = apply_other ]; then
  echo "[5/6] git am"
  [ -z "$(git status --porcelain --untracked-files=no)" ] || die "tracked files have uncommitted changes; commit or stash them first"
  [ -e "$NEW_DIR" ] && die "$NEW_DIR already exists but package 15 is not applied; move it away first"
  [ -e "$NEW_NOTE" ] && die "$NEW_NOTE already exists but package 15 is not applied; move it away first"
  check_list "$HERE/pkg15-sha256-before.txt" || die "before-hashes differ"
  ID=""
  [ -n "$(git config user.name)" ] && [ -n "$(git config user.email)" ] || ID="-c user.name=planner -c user.email=planner@example.invalid"
  # shellcheck disable=SC2086
  if ! git $ID am --whitespace=nowarn "$PATCH"; then git am --abort >/dev/null 2>&1; die "git am failed (aborted, repository unchanged)"; fi
  TREE="$(git rev-parse 'HEAD^{tree}')"
  if [ "$MODE" = apply_exact ]; then
    [ "$TREE" = "$AFTER_TREE" ] || die "tree after git am is $TREE, expected $AFTER_TREE (inspect; 'git reset --hard HEAD~1' undoes it)"
    echo "      OK tree $TREE"
  else
    echo "      applied on a different starting point; new tree $TREE (expected-tree check skipped, file hashes checked below)"
  fi
else
  echo "[5/6] git am skipped: package 15 is already applied"
fi

echo "[6/6] after-hashes"
check_list "$HERE/pkg15-sha256-after.txt" || die "after-hashes differ"
echo "      OK (10 files)"
echo
echo "DONE. HEAD $(git rev-parse HEAD)  tree $(git rev-parse 'HEAD^{tree}')"
echo "Nothing was pushed. Push is the user's decision (git push origin HEAD:main)."
echo "Next: the executor follows $NEW_DIR/说明.md"
