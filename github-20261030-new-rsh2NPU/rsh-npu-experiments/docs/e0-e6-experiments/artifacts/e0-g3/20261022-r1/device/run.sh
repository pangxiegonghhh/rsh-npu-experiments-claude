#!/bin/bash
cd /data/e0-g3-20261022-r1
/usr/local/python3.11.15/bin/python scripts/e0_g3.py run --parent /data/e0-supplement-r1 --out /data/e0-g3-20261022-r1
G3_RC=$?
printf 'G3_RC=%s\n' "$G3_RC" > driver.rc
exit "$G3_RC"
