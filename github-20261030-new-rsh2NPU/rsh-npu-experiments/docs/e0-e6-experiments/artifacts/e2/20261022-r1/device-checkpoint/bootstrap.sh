#!/bin/bash
cd /data/e2-20261022-r1
/usr/local/python3.11.15/bin/python bootstrap.py
rc=$?
printf 'BOOTSTRAP_RC=%s\n' "$rc" > bootstrap.rc
exit "$rc"
