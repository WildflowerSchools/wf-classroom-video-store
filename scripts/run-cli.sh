#!/bin/bash

cmd_extras=""
if [ ! -z "${RETENTION_DELTA}" ]; then
    cmd_extras="${cmd_extras} --retention-delta ${RETENTION_DELTA}"
fi

if [ ! -z "${DRY}"  ] && [ "${DRY}" = "true" ]; then
    cmd_extras="${cmd_extras} --dry"
fi

IFS=',' read -r -a environment_ids <<< "${ENVIRONMENT_IDS}"
if [ ${#environment_ids[@]} -gt 0 ]; then
    for eid in "${environment_ids[@]}"
    do
      cmd_extras="${cmd_extras} --environment-id `echo ${eid} | xargs echo -n`"
    done
fi

python -m classroom_video.console delete-video ${cmd_extras}
