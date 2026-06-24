#!/bin/bash
# Parallel LIBERO-Plus regeneration -> LeRobot conversion -> hub push -> cleanup.
#
# Reads a combo manifest (robot \t dim \t suite, one per line; see gen_libero_plus_manifest.py)
# and runs CONCURRENCY workers from an xargs pool. Each worker handles ONE combo end-to-end:
#   regen (regenerate_libero_plus_dataset.py) -> convert+push (libero_h5.py) -> delete raw.
# Successes go to OliverHausdoerfer/libero_plus_<dim>_<suite>_<robot>${CAMSUFFIX}, failed replays
# to the same name + _failures. A combo is skipped if its .done marker exists (resumable).
#
# Camera set is chosen with CAMERAS (default|additional); pass --include-mix sizing via INCLUDE_MIX.
# MUST run inside the libero_plus conda env (the fork). Safety knobs: CONCURRENCY, PER_COMBO_GB.

set -u

PYTHON="${PYTHON:-/home/admin_07/miniconda3/envs/libero_plus/bin/python}"
BASE=/home/admin_07/project_repos/any4lerobot
RAW_ROOT="$BASE/libero_datasets"                       # original per-suite demos (action source)
REGEN_ROOT="$BASE/libero_datasets_regenerated"
LEROBOT_ROOT="$BASE/lerobot_datasets"
HUB_USER=OliverHausdoerfer

MANIFEST="${1:-manifest.txt}"
CAMERAS="${CAMERAS:-default}"
CAMSUFFIX="_${CAMERAS}Cams"
INCLUDE_MIX="${INCLUDE_MIX:-1}"                          # 1 -> --include-mix, 0 -> --no-include-mix
CAP_PER_DIM="${CAP_PER_DIM:-}"                           # optional subsample for pilots
CONCURRENCY="${CONCURRENCY:-4}"
PER_COMBO_GB="${PER_COMBO_GB:-40}"                       # est. peak raw disk per combo
MIN_FREE_GB="${MIN_FREE_GB:-120}"                        # per-worker guard before regen

LOGDIR="$BASE/libero2lerobot/experiments/libero_plus_logs"
STATEDIR="$LOGDIR/.done"
mkdir -p "$LOGDIR" "$STATEDIR"

export SVT_LOG=1
export HF_DATASETS_DISABLE_PROGRESS_BARS=TRUE
export HDF5_USE_FILE_LOCKING=FALSE
# Fork-local libero config so bddl_files/assets resolve to LIBERO-plus, not the global ~/.libero
# (which points at a different LIBERO checkout shared by the other conda envs).
export LIBERO_CONFIG_PATH="${LIBERO_CONFIG_PATH:-$BASE/LIBERO-plus/.libero}"

log() { echo "[$(date +%F_%T)] $*"; }

free_gb() { df --output=avail -BG "$BASE" | tail -1 | tr -dc '0-9'; }

# --- preflight: estimated peak disk for the whole pool ---
need_gb=$((CONCURRENCY * PER_COMBO_GB))
have_gb=$(free_gb)
log "preflight: ${have_gb}G free, pool needs ~${need_gb}G (CONCURRENCY=$CONCURRENCY x PER_COMBO_GB=${PER_COMBO_GB}G)"
if [ "$have_gb" -lt "$need_gb" ]; then
    log "ABORT: insufficient disk for the pool"
    exit 1
fi
if [ ! -f "$MANIFEST" ]; then
    log "ABORT: manifest not found: $MANIFEST"
    exit 1
fi

# Worker for one combo. Args: robot dim suite
worker() {
    local robot="$1" dim="$2" suite="$3"
    local robot_lc; robot_lc=$(echo "$robot" | tr '[:upper:]' '[:lower:]')
    local tag="libero_plus_${dim}_${suite}_${robot_lc}${CAMSUFFIX}"
    local marker="$STATEDIR/${tag}.done"
    local raw="$REGEN_ROOT/${tag}"
    local raw_fail="${raw}_failures"
    local repo="$HUB_USER/${tag}"
    local mixflag; [ "$INCLUDE_MIX" = "1" ] && mixflag="--include-mix" || mixflag="--no-include-mix"
    local capflag=""; [ -n "$CAP_PER_DIM" ] && capflag="--cap-per-dim $CAP_PER_DIM"

    if [ -f "$marker" ]; then
        log "SKIP $tag (done marker present)"
        return 0
    fi
    local fg; fg=$(free_gb)
    if [ "$fg" -lt "$MIN_FREE_GB" ]; then
        log "SKIP $tag: ${fg}G free < ${MIN_FREE_GB}G guard"
        return 0
    fi
    log "START $tag (${fg}G free)"

    if ! $PYTHON libero_utils/regenerate_libero_plus_dataset.py \
            --resolution 256 \
            --perturbation_dim "$dim" \
            --libero_task_suite "$suite" \
            --robot "$robot" \
            --replay_mode delta \
            --cameras "$CAMERAS" \
            $mixflag $capflag \
            --libero_raw_data_root "$RAW_ROOT" \
            --libero_target_dir "$raw" \
            </dev/null >"$LOGDIR/${tag}_regen.log" 2>&1; then
        log "regen FAILED $tag (see ${tag}_regen.log) — keeping raw, skipping"
        return 0
    fi

    if [ ! -d "$raw" ]; then
        log "regen produced no successes for $tag — marking done"
        rm -rf "$raw_fail"
        touch "$marker"
        return 0
    fi

    if $PYTHON libero_h5.py \
            --src-paths "$raw" \
            --output-path "$LEROBOT_ROOT" \
            --robot-type "$robot_lc" \
            --cameras "$CAMERAS" \
            --executor local \
            --workers 30 \
            --push-to-hub \
            --repo-id "$repo" \
            </dev/null >"$LOGDIR/${tag}_convert.log" 2>&1; then
        log "convert+push OK $tag -> $repo"
        rm -rf "$raw" "$LEROBOT_ROOT/${tag}_lerobot"
    else
        log "convert/push FAILED $tag (see ${tag}_convert.log) — keeping raw, skipping"
        return 0
    fi

    if [ -d "$raw_fail" ] && [ -n "$(ls -A "$raw_fail" 2>/dev/null)" ]; then
        if $PYTHON libero_h5.py \
                --src-paths "$raw_fail" \
                --output-path "$LEROBOT_ROOT" \
                --robot-type "$robot_lc" \
                --cameras "$CAMERAS" \
                --executor local \
                --workers 30 \
                --push-to-hub \
                --repo-id "${repo}_failures" \
                </dev/null >"$LOGDIR/${tag}_convert_failures.log" 2>&1; then
            log "convert+push OK $tag failures -> ${repo}_failures"
            rm -rf "$raw_fail" "$LEROBOT_ROOT/${tag}_failures_lerobot"
        else
            log "convert/push FAILED $tag failures — keeping raw"
        fi
    else
        rm -rf "$raw_fail"
    fi

    touch "$marker"
    log "DONE $tag"
}
export -f worker log free_gb
export PYTHON BASE RAW_ROOT REGEN_ROOT LEROBOT_ROOT HUB_USER CAMERAS CAMSUFFIX \
       INCLUDE_MIX CAP_PER_DIM MIN_FREE_GB LOGDIR STATEDIR

# Feed the manifest (skip blank/comment lines) into the worker pool.
grep -vE '^\s*(#|$)' "$MANIFEST" \
    | xargs -P "$CONCURRENCY" -I {} bash -c 'worker $(printf "%s" "{}")'

log "ALL COMBOS PROCESSED (manifest: $MANIFEST, cameras: $CAMERAS)"
