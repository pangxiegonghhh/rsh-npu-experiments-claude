#!/bin/bash
cd /data/e1-20261022-r1
/usr/local/python3.11.15/bin/python scripts/e1_experiment.py run /data/e1-20261022-r1
rc=$?
printf 'E1_RC=%s\n' "$rc" > driver.rc
exit "$rc"
