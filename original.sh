#!/bin/bash

DELETE_OLDER_THAN=${1:-90}

# Log start timestamp
echo "`date` - start: will clean out data older than $DELETE_OLDER_THAN days in /gpfs/research/eoas"

# make this script configurable
BEFORE_CLEAN=`ssh n22-gpfs-quorum /usr/lpp/mmfs/bin/mmlsquota --block-size=auto -j eoas research | tail -n 1 | awk '{ print $3 }'`

# Find all files older than the given number of days and delete them
# 2023-11-17 - Changed mtime to atime at request of department - Casey McL (see https://sforce.co/3G5aUiA)
find /gpfs/research/eoas/* -type f -atime +${DELETE_OLDER_THAN} -print -exec rm {} \;
find /gpfs/research/eoas/* -type d -atime +${DELETE_OLDER_THAN} -print -exec rmdir {} \;

# Check used
AFTER_CLEAN=`ssh n22-gpfs-quorum /usr/lpp/mmfs/bin/mmlsquota --block-size=auto -j eoas research | tail -n 1 | awk '{ print $3 }'`

# Log finished
echo "`date` - finish: before cleanup ($BEFORE_CLEAN) --- after cleanup: ($AFTER_CLEAN)"

