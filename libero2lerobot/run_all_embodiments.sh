#!/bin/bash
# Sequential cross-embodiment LIBERO regeneration -> LeRobot conversion -> hub push -> cleanup.
# Disk constraint: only one regenerated raw suite may exist at a time, so raw HDF5s and the
# local LeRobot copy are deleted only after a successful push.
#
# Failure policy:
#  - regeneration fails  -> delete partial raw output, continue with next combo
#  - convert/push fails  -> keep artifacts for debugging and ABORT (disk would fill up,
#                           and a push failure is likely systematic e.g. auth/network)

set -u

PYTHON=/home/admin_07/miniconda3/envs/any4lerobot/bin/python
BASE=/home/admin_07/project_repos/any4lerobot
LOGDIR=$BASE/libero2lerobot/experiments/embodiment_pipeline_logs
mkdir -p "$LOGDIR"

export SVT_LOG=1
export HF_DATASETS_DISABLE_PROGRESS_BARS=TRUE
export HDF5_USE_FILE_LOCKING=FALSE

# UR5e first (libero_object already done and pushed), then the new embodiments.
# Small suites first per embodiment for an early success-rate signal; libero_90 last.
COMBOS=(
    "UR5e libero_spatial"
    "UR5e libero_goal"
    "UR5e libero_10"
    "Kinova3 libero_object"
    "Kinova3 libero_spatial"
    "Kinova3 libero_goal"
    "Kinova3 libero_10"
    "IIWA libero_object"
    "IIWA libero_spatial"
    "IIWA libero_goal"
    "IIWA libero_10"
    "Sawyer libero_object"
    "Sawyer libero_spatial"
    "Sawyer libero_goal"
    "Sawyer libero_10"
    # libero_90 deferred (~200 GB raw + ~2.5 h regen per embodiment):
    # "UR5e libero_90"
    # "Kinova3 libero_90"
    # "IIWA libero_90"
    # "Sawyer libero_90"
)

# Approximate raw regeneration size + headroom, from the libero_object run (22 GB / 10 tasks).
# All 500 episodes are now kept (successes + failures), so budget for the full suite.
required_gb() { [ "$1" = "libero_90" ] && echo 320 || echo 70; }

for combo in "${COMBOS[@]}"; do
    read -r ROBOT SUITE <<<"$combo"
    robot_lc=$(echo "$ROBOT" | tr '[:upper:]' '[:lower:]')
    TAG="${SUITE}_${robot_lc}"
    RAW="$BASE/libero_datasets_regenerated/${TAG}_additionalCams"
    RAW_FAIL="${RAW}_failures"
    LEROBOT="$BASE/lerobot_datasets/${TAG}_additionalCams_lerobot"
    LEROBOT_FAIL="$BASE/lerobot_datasets/${TAG}_additionalCams_failures_lerobot"
    REPO="OliverHausdoerfer/${TAG}_additionalCams"
    REPO_FAIL="OliverHausdoerfer/${TAG}_additionalCams_failures"

    free_gb=$(df --output=avail -BG "$BASE" | tail -1 | tr -dc '0-9')
    need_gb=$(required_gb "$SUITE")
    if [ "$free_gb" -lt "$need_gb" ]; then
        echo "[$(date +%F_%T)] ABORT before $TAG: ${free_gb}G free < ${need_gb}G required"
        exit 1
    fi

    echo "[$(date +%F_%T)] START $TAG (${free_gb}G free)"

    if $PYTHON libero_utils/regenerate_libero_dataset.py \
        --resolution 256 \
        --libero_task_suite "$SUITE" \
        --robot "$ROBOT" \
        --replay_mode delta \
        --libero_raw_data_dir "$BASE/libero_datasets/$SUITE" \
        --libero_target_dir "$RAW" \
        </dev/null >"$LOGDIR/${TAG}_regen.log" 2>&1; then
        echo "[$(date +%F_%T)] regen OK $TAG: $(grep 'episodes replayed' "$LOGDIR/${TAG}_regen.log" | tail -1 | xargs)"
    else
        echo "[$(date +%F_%T)] regen FAILED $TAG (see ${TAG}_regen.log) — skipping combo"
        rm -rf "$RAW" "$RAW_FAIL"
        continue
    fi

    # Convert + push successes, then failures (each to its own repo). The failures
    # directory may not exist if every replay succeeded — skip it then.
    convert_push() {  # args: src_dir repo lerobot_out logsuffix
        $PYTHON libero_h5.py \
            --src-paths "$1" \
            --output-path "$BASE/lerobot_datasets" \
            --robot-type "$robot_lc" \
            --executor local \
            --tasks-per-job 3 \
            --workers 30 \
            --push-to-hub \
            --repo-id "$2" \
            </dev/null >"$LOGDIR/${TAG}_$4.log" 2>&1
    }

    if convert_push "$RAW" "$REPO" "$LEROBOT" convert; then
        echo "[$(date +%F_%T)] convert+push OK $TAG -> $REPO"
        rm -rf "$RAW" "$LEROBOT"
    else
        echo "[$(date +%F_%T)] convert/push FAILED $TAG (see ${TAG}_convert.log) — artifacts kept, ABORTING"
        exit 1
    fi

    if [ -d "$RAW_FAIL" ] && [ -n "$(ls -A "$RAW_FAIL" 2>/dev/null)" ]; then
        if convert_push "$RAW_FAIL" "$REPO_FAIL" "$LEROBOT_FAIL" convert_failures; then
            echo "[$(date +%F_%T)] convert+push OK $TAG failures -> $REPO_FAIL"
            rm -rf "$RAW_FAIL" "$LEROBOT_FAIL"
        else
            echo "[$(date +%F_%T)] convert/push FAILED $TAG failures (see ${TAG}_convert_failures.log) — artifacts kept, ABORTING"
            exit 1
        fi
    else
        echo "[$(date +%F_%T)] no failures for $TAG — skipping failures push"
        rm -rf "$RAW_FAIL"
    fi

    echo "[$(date +%F_%T)] cleanup OK $TAG"
done

echo "[$(date +%F_%T)] ALL COMBOS DONE"
