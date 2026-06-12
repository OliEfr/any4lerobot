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
    "UR5e libero_90"
    "Kinova3 libero_object"
    "Kinova3 libero_spatial"
    "Kinova3 libero_goal"
    "Kinova3 libero_10"
    "Kinova3 libero_90"
    "IIWA libero_object"
    "IIWA libero_spatial"
    "IIWA libero_goal"
    "IIWA libero_10"
    "IIWA libero_90"
    "Sawyer libero_object"
    "Sawyer libero_spatial"
    "Sawyer libero_goal"
    "Sawyer libero_10"
    "Sawyer libero_90"
)

# Approximate raw regeneration size + headroom, from the libero_object run (22 GB / 10 tasks).
required_gb() { [ "$1" = "libero_90" ] && echo 260 || echo 50; }

for combo in "${COMBOS[@]}"; do
    read -r ROBOT SUITE <<<"$combo"
    robot_lc=$(echo "$ROBOT" | tr '[:upper:]' '[:lower:]')
    TAG="${SUITE}_${robot_lc}"
    RAW="$BASE/libero_datasets_regenerated/${TAG}_additionalCams"
    LEROBOT="$BASE/lerobot_datasets/${TAG}_additionalCams_lerobot"
    REPO="OliverHausdoerfer/${TAG}_additionalCams"

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
        rm -rf "$RAW"
        continue
    fi

    if $PYTHON libero_h5.py \
        --src-paths "$RAW" \
        --output-path "$BASE/lerobot_datasets" \
        --robot-type "$robot_lc" \
        --executor local \
        --tasks-per-job 3 \
        --workers 30 \
        --push-to-hub \
        --repo-id "$REPO" \
        </dev/null >"$LOGDIR/${TAG}_convert.log" 2>&1; then
        echo "[$(date +%F_%T)] convert+push OK $TAG -> $REPO"
        rm -rf "$RAW" "$LEROBOT"
        echo "[$(date +%F_%T)] cleanup OK $TAG"
    else
        echo "[$(date +%F_%T)] convert/push FAILED $TAG (see ${TAG}_convert.log) — artifacts kept, ABORTING"
        exit 1
    fi
done

echo "[$(date +%F_%T)] ALL COMBOS DONE"
