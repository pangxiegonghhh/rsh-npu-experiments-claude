#!/bin/bash
cd /data/e1-20261022-r1
/usr/local/python3.11.15/bin/python continue-build.py
rc=$?
printf 'BUILD_RC=%s\n' "$rc" > continue-build.rc
exit "$rc"
