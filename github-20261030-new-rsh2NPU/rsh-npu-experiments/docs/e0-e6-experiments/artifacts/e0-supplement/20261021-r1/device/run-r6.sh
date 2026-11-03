while kill -0 11680 2>/dev/null || kill -0 11681 2>/dev/null; do sleep 2; done
grep -Fq 'Built target e0_split' build-r6.log || exit 1
grep -Fq 'Built target rsh_guarded' integrated-build-r6.log || exit 1
for name in direct-expanded integrated-direct integrated-normal split-normal split-direct; do if [ -d results/$name ]; then mv results/$name results/$name-before-sync; fi; done
mv finish.log finish-before-sync.log
mv finish.rc finish-before-sync.rc
bash -e post-normal.sh > post-sync.log 2>&1 || exit 1
python scripts/e0_finish.py > finish.log 2>&1
echo FINISH_RC=$? > finish.rc
