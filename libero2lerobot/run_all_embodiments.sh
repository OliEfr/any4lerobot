#!/bin/bash
# Cross-embodiment LIBERO regeneration -> LeRobot conversion -> hub push -> cleanup.
#
# Phase 1: the four small suites per embodiment with the regenerations running in
#          parallel (~30 GB raw each), then sequential convert+push per suite.
# Phase 2: libero_90 per embodiment, fully sequential (raw output is ~250 GB each,
#          so only one may exist at a time).
#
# Successes go to OliverHausdoerfer/<suite>_<robot>${CAMSUFFIX}, failed replays
# to the same name + _failures. Local data is deleted only after a successful push.
#
# Failure policy:
#  - regeneration fails  -> delete partial raw output, skip that suite
#  - convert/push fails  -> keep artifacts for debugging and ABORT (disk would fill
#                           up, and a push failure is likely systematic e.g. auth)

set -u

PYTHON=/home/admin_07/miniconda3/envs/any4lerobot/bin/python
BASE=/home/admin_07/project_repos/any4lerobot
LOGDIR=$BASE/libero2lerobot/experiments/embodiment_pipeline_logs
mkdir -p "$LOGDIR"

export SVT_LOG=1
export HF_DATASETS_DISABLE_PROGRESS_BARS=TRUE
export HDF5_USE_FILE_LOCKING=FALSE

ROBOTS=(UR5e Kinova3 IIWA Sawyer)
SMALL_SUITES=(libero_object libero_spatial libero_goal libero_10)

# Camera-view tag appended to every regen dir, LeRobot dir, and hub repo name.
# _additionalCams = frontview+sideview; _defaultCams = agentview+robot0_eye_in_hand.
# Must match the camera set currently active in regenerate_libero_dataset.py / config.py / libero_utils.py.
CAMSUFFIX="_defaultCams"

log() { echo "[$(date +%F_%T)] $*"; }

check_disk() { # args: need_gb label
    local free_gb
    free_gb=$(df --output=avail -BG "$BASE" | tail -1 | tr -dc '0-9')
    if [ "$free_gb" -lt "$1" ]; then
        log "ABORT before $2: ${free_gb}G free < $1G required"
        exit 1
    fi
    log "START $2 (${free_gb}G free)"
}

regen() { # args: robot suite tag
    $PYTHON libero_utils/regenerate_libero_dataset.py \
        --resolution 256 \
        --libero_task_suite "$2" \
        --robot "$1" \
        --replay_mode delta \
        --libero_raw_data_dir "$BASE/libero_datasets/$2" \
        --libero_target_dir "$BASE/libero_datasets_regenerated/${3}${CAMSUFFIX}" \
        </dev/null >"$LOGDIR/${3}_regen.log" 2>&1
}

convert_push() { # args: src_dir repo_id robot_lc logfile
    $PYTHON libero_h5.py \
        --src-paths "$1" \
        --output-path "$BASE/lerobot_datasets" \
        --robot-type "$3" \
        --executor local \
        --tasks-per-job 3 \
        --workers 30 \
        --push-to-hub \
        --repo-id "$2" \
        </dev/null >"$4" 2>&1
}

# Convert + push successes then failures for one regenerated suite, with cleanup.
# Aborts the whole pipeline on a push failure.
publish() { # args: robot_lc tag
    local robot_lc=$1 TAG=$2
    local RAW="$BASE/libero_datasets_regenerated/${TAG}${CAMSUFFIX}"
    local RAW_FAIL="${RAW}_failures"
    local REPO="OliverHausdoerfer/${TAG}${CAMSUFFIX}"

    if convert_push "$RAW" "$REPO" "$robot_lc" "$LOGDIR/${TAG}_convert.log"; then
        log "convert+push OK $TAG -> $REPO"
        rm -rf "$RAW" "$BASE/lerobot_datasets/${TAG}${CAMSUFFIX}_lerobot"
    else
        log "convert/push FAILED $TAG (see ${TAG}_convert.log) — artifacts kept, ABORTING"
        exit 1
    fi

    if [ -d "$RAW_FAIL" ] && [ -n "$(ls -A "$RAW_FAIL" 2>/dev/null)" ]; then
        if convert_push "$RAW_FAIL" "${REPO}_failures" "$robot_lc" "$LOGDIR/${TAG}_convert_failures.log"; then
            log "convert+push OK $TAG failures -> ${REPO}_failures"
            rm -rf "$RAW_FAIL" "$BASE/lerobot_datasets/${TAG}${CAMSUFFIX}_failures_lerobot"
        else
            log "convert/push FAILED $TAG failures (see ${TAG}_convert_failures.log) — artifacts kept, ABORTING"
            exit 1
        fi
    else
        log "no failures for $TAG — skipping failures push"
        rm -rf "$RAW_FAIL"
    fi

    log "cleanup OK $TAG"
}

regen_result() { # args: tag -> prints final success-rate line from the regen log
    grep 'episodes replayed' "$LOGDIR/${1}_regen.log" | tail -1 | xargs
}

# ---------- Phase 1: small suites, regen 4x parallel per robot ----------
for ROBOT in "${ROBOTS[@]}"; do
    robot_lc=$(echo "$ROBOT" | tr '[:upper:]' '[:lower:]')
    check_disk 160 "small suites $ROBOT (parallel regen)"

    pids=()
    for SUITE in "${SMALL_SUITES[@]}"; do
        regen "$ROBOT" "$SUITE" "${SUITE}_${robot_lc}" &
        pids+=($!)
    done

    ok_suites=()
    for idx in "${!SMALL_SUITES[@]}"; do
        SUITE="${SMALL_SUITES[$idx]}"
        TAG="${SUITE}_${robot_lc}"
        if wait "${pids[$idx]}"; then
            log "regen OK $TAG: $(regen_result "$TAG")"
            ok_suites+=("$SUITE")
        else
            log "regen FAILED $TAG (see ${TAG}_regen.log) — skipping suite"
            rm -rf "$BASE/libero_datasets_regenerated/${TAG}${CAMSUFFIX}" \
                   "$BASE/libero_datasets_regenerated/${TAG}${CAMSUFFIX}_failures"
        fi
    done

    for SUITE in "${ok_suites[@]}"; do
        publish "$robot_lc" "${SUITE}_${robot_lc}"
    done
done

# ---------- Phase 2: libero_90, sequential ----------
for ROBOT in "${ROBOTS[@]}"; do
    robot_lc=$(echo "$ROBOT" | tr '[:upper:]' '[:lower:]')
    TAG="libero_90_${robot_lc}"
    check_disk 320 "$TAG"
    if regen "$ROBOT" libero_90 "$TAG"; then
        log "regen OK $TAG: $(regen_result "$TAG")"
    else
        log "regen FAILED $TAG (see ${TAG}_regen.log) — skipping combo"
        rm -rf "$BASE/libero_datasets_regenerated/${TAG}${CAMSUFFIX}" \
               "$BASE/libero_datasets_regenerated/${TAG}${CAMSUFFIX}_failures"
        continue
    fi
    publish "$robot_lc" "$TAG"
done

log "ALL COMBOS DONE"
