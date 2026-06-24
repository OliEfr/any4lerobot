# Plan: Regenerate LIBERO-Plus (4 render dims) across embodiments + additional cameras

## Context

`libero2lerobot/` already regenerates **standard LIBERO** across 4 non-Panda embodiments
(UR5e, Kinova3, IIWA, Sawyer) and two camera sets, by replaying the original Panda
`(state, action)` demos in a freshly-built env with a chosen robot + cameras, success-filtering,
and converting to LeRobot v3 (`run_all_embodiments.sh` → `regenerate_libero_dataset.py` →
`libero_h5.py`).

We now want the same for **LIBERO-Plus**, scoped to the **four render-only perturbation dimensions**
the user wants: **camera viewpoint, lighting, background texture, sensor noise** (a subset of
LIBERO-Plus's 6 training dims — it also has language + compounding-objects, which we omit). These
are render-only, so they leave the action trajectory valid → we reuse our existing original LIBERO
demos as the action source (no published-dataset actions, no episode↔variant mapping). Physics dims
(object-displacement, robot-init-pose) are excluded by LIBERO-Plus itself and confirmed absent.

Requirements: (1) **exact LIBERO-Plus perturbations** via its fork + `assets.zip`; (2) embodiments
**Panda + UR5e/Kinova3/IIWA/Sawyer**; (3) **both camera sets** — default agentview+wrist AND
frontview+sideview — selected **one at a time** via a flag (front/sideview perturbed as discussed);
(4) **per-dimension** datasets; (5) scale matched to the **original HF dataset** (full per-dim instance
set); (6) **switch back to standard-LIBERO regeneration** (also with embodiments + cameras); (7) a
**disk-gated parallel runner** (concurrency across robot×dim×suite).

**Eval target = standard LIBERO-Plus eval ONLY** (Panda, agentview+wrist, 7 dims). This defines a
conformance split:
- **Eval-conformant core**: **Panda × default cams × the 4 dims** — matches the eval + original
  `lerobot/libero_plus` (same suites, cameras, state/action, perturbation realism, ~size). Generate
  this first.
- **Auxiliary** (still wanted): **non-Panda embodiments** and the **front+sideview** cam set — do NOT
  directly conform (different embodiment/viewpoints); value is cross-embodiment / view-robustness and
  possible co-training benefit to the Panda eval. Generated as separate passes.
- **Coverage gap**: eval tests 7 dims; we train 4 → **language + objects-layout + robot-init stay
  zero-shot** (language by choice; the 2 physics dims untrainable via replay). Correctness-conform on
  the 4 we do; coverage-incomplete on the other 3.
- **Feature-key alignment**: our keys are `observation.images.image` (agentview) + `..wrist_image`;
  original uses `front`+`wrist`; eval doc references `image`+`image2`. Not a blocker, but the eval run's
  observation-mapping must point the env's agentview/wrist cameras at our dataset's exact keys — verify
  before training.

### How LIBERO-Plus made its training set (EMPIRICALLY VERIFIED — drives sizing and scope)
- **4 suites only — libero_90 DROPPED** (confirmed twice: 40-distinct-tasks in the LeRobot set, and
  `task_classification.json` has exactly `libero_spatial/object/goal/10`). → **we drop it too.**
- **One perturbation dimension per demo/rollout — NEVER combined.** Confirmed from the eval taxonomy:
  all 10,030 eval tasks carry exactly one `category` + one `difficulty_level` (1–5). Categories
  (≈balanced): Sensor Noise 1601, Camera 1599, Robot-Init 1550, Language 1537, Objects-Layout 1525,
  Light 1142, Background-Texture 1076. So each demo is perturbed independently per dimension; demos are
  reused across dimensions; no trajectory stacks multiple dims.
- **`libero_mix` = a 2nd round of perturbations on the SAME tasks (no new scenes).** VERIFIED: its 50
  base tasks are ALL in the per-suite folders (0 new); for a shared task the per-suite folder has
  `light_1..50` AND mix has `light_1..50` (indices restart). So per-suite = **1 perturbation/demo**
  (~50/task), and per-suite + mix = **2/demo** (~100/task ≈ 4,000/dim, matching the paper). NOT combined
  perturbations (only 173/8,120 files have 2 tokens). **Include mix to match the original ~4,000/dim
  size**; omit it for a 1×/demo (~2,000/dim) half-size set.
- **Token → dimension map** (VERIFIED by counting files in the clone): `_light_`→Light (4000 bddls),
  `_table_`/`_tb_`→Background Texture (2562+1790 bddls). **Camera, Sensor-Noise (and Robot-Init) have 0
  bddl files** — they are encoded in the task NAME (`_view_…_initstate_…[_noise_…]`) and applied
  **natively** by the fork's `ControlEnv` at runtime (camera→`agentview` only; noise→`agentview_image`
  only). We synthesize those names from sampled params; additional cams get a re-application hook.

### Sizing rule — NO `num_instances` param
The per-demo count is data-determined, not a free integer. Two knobs only:
- **`--include-mix`** (default on, to match the original ~4,000/dim): light/texture iterate the bddl
  files that exist (per-suite + mix → 2/demo); camera/noise generate 2 samples/demo. Off → 1/demo.
- **`--cap-per-dim N`**: subsample for pilots / disk pressure.

Per dim, per robot:
- **Light**: iterate all `_light_` bddls (per-suite [+mix]) ≈ 2,000 [4,000], each paired with its base-task demo.
- **Texture**: iterate all `_table_`/`_tb_` bddls ≈ 2,176 [4,352], paired with base-task demos.
- **Camera / Noise**: sample 1 [2] param set(s) per demo, synthesized into the `_view_…`/`_noise_…` task
  name (native on agentview; re-applied to the extra views for additional cams).
This yields **~16k trajs/robot** (with mix) across the 4 dims → meets/exceeds the published 14,347.

## Approach

Drive from the **LIBERO-Plus fork** (its perturbation code + assets + params), overriding **robot +
cameras**, replaying the matching original LIBERO demo actions, success-filtering, saving HDF5,
converting per-combo. LIBERO-Plus-specific logic lives in a **separate, new
`regenerate_libero_plus_dataset.py`** (NOT folded into `regenerate_libero_dataset.py`, per the user's
constraint). The new script **imports the pure replay/init helpers** from
`regenerate_libero_dataset.py` (`drive_to_start_and_splice`, `is_noop`, `set_controller_absolute`,
`get_eef_goal_action`, `get_libero_dummy_action`, `get_source_panda_env`, `ROBOT_JOINT_DIMS`) and adds
its own work-item-driven outer loop + per-dimension perturbation. The fork lives in its own conda env
(it replaces vanilla `libero`).

> **Why a separate script, not a `--libero_plus` flag.** User directive: keep
> `regenerate_libero_dataset.py` untouched except for the dynamic-camera change. The standard script
> iterates a `task_suite`; the Plus script iterates *perturbation work items* (perturbed bddl instances
> / programmatic params paired with base-task demos) — a different outer loop. The two share only the
> per-demo replay primitives, which are already module-level functions safe to import (argparse is
> under `__main__`; `import custom_robots` at module top is wanted in the fork env too).
> **Intentional duplication:** the ~80-line per-demo *replay+save* inner loop is copied into the Plus
> script (adapted to apply the perturbation + log provenance attrs) rather than extracted into a shared
> module, because extracting it would mean editing `regenerate_libero_dataset.py` beyond the camera
> change. Accept this small duplication to honor the untouched constraint.
> **Sole edit to `regenerate_libero_dataset.py` = the dynamic-camera change** (below). The Plus script
> imports `get_libero_env` + `CAMERA_SETS` and never re-declares camera logic, so the standard and Plus
> paths stay in lockstep on camera handling.

### Dynamic camera selection (replaces the b7d34c8 comment-toggle)
Today cameras are switched by hand-editing commented blocks across `regenerate_libero_dataset.py`,
`config.py`, `libero_utils.py` plus a hand-set `CAMSUFFIX` in `run_all_embodiments.sh`
(commit `b7d34c8`). Replace this with a single **camera registry** in `config.py` — the one source of
truth, consumed by both regeneration scripts and the converter:
```python
# config.py
CAMERA_SETS = {
    # set -> list of (env_render_cam, env_obs_image_key, hdf5_rgb_key, lerobot_feature_key)
    "default": [
        ("agentview",          "agentview_image",          "agentview_rgb",   "observation.images.image"),
        ("robot0_eye_in_hand", "robot0_eye_in_hand_image", "eye_in_hand_rgb", "observation.images.wrist_image"),
    ],
    "additional": [
        ("frontview", "frontview_image", "frontview_rgb", "observation.images.frontview_image"),
        ("sideview",  "sideview_image",  "sideview_rgb",  "observation.images.sideview_image"),
    ],
}
```
A runtime `--cameras {default,additional}` flag (default `default`) selects the set. `--cameras default`
reproduces today's active output exactly (agentview + eye-in-hand, `_defaultCams` repos); `--cameras
additional` reproduces the prior frontview+sideview `_additionalCams` output. The commented-out
alternative blocks in all files are **deleted** — the registry replaces them.
`regenerate_libero_plus_dataset.py` consumes the same registry, so cross-embodiment LIBERO-Plus gets
identical camera handling for free.

**Two envs (mandatory):**
- `any4lerobot` (existing, vanilla libero) → **standard-LIBERO** regeneration (`regenerate_libero_dataset.py`)
  = the "switch back".
- new `libero_plus` (fork + `assets.zip`, `custom_robots` importable) → **LIBERO-Plus** regeneration
  (`regenerate_libero_plus_dataset.py`).
Both scripts share `config.py` / `libero_utils.py` / `libero_h5.py`. The camera registry
(`CAMERA_SETS`, see *Dynamic camera selection* above) lives in `config.py` and is the single switch
point for both regeneration scripts and the converter.
Switch back = run the standard script in the vanilla env.

### Per-dimension mechanism (how "exact" each is) — VERIFIED against the cloned fork

**Key finding (verified in `LIBERO-plus/libero/libero/envs/env_wrapper.py` + `problems/*.py`):** the fork's
`ControlEnv`/`OffScreenRenderEnv` applies camera, sensor-noise, and robot-init **natively, parsed from the
task NAME** `…_view_<h>_<v>_<scale>_<endrot>_<endvert>_initstate_<n>[_noise_<m>]`. `_view_`, `_noise_`,
`_initstate_` have **0 bddl files** — they are virtual names stripped back to the base bddl at runtime.
So for the **default cam set** we do NOT write a `CameraModder` or our own cv2 kernels: we **synthesize the
perturbed task name from our sampled params** and let the env apply it. **Caveat:** the native camera
transform moves **only `agentview`** (`_setup_camera`, e.g. `libero_kitchen_tabletop_manipulation.py:349`;
frontview is set to a *fixed* pose), and the native noise blurs **only `obs["agentview_image"]`**
(`env_wrapper.py:285-348`). The user requires the perturbation on **frontview+sideview too**, so the
**additional cam set needs an explicit hook that re-applies the SAME params to those views, reusing the
fork's own code** (no new kernels).

| Dim | Source / params | Default cams (agentview) | Additional cams (frontview+sideview) |
|---|---|---|---|
| **Lighting** | `_light_` **bddl files** (per-suite + mix; ≈4,000 verified) | Instantiate perturbed bddl; scene-level, camera-agnostic ✅ | Same — scene-level, both views correct ✅ |
| **Background texture** | `_table_`/`_tb_` **bddl files** (= "Background Textures"; 2562+1790 verified) | Instantiate perturbed bddl; scene-level ✅ | Same — scene-level ✅ |
| **Camera** | **Sampled params** (dist 1.01–2.0×, az/elev 15–75°, rpy 2–10°), formatted into the `_view_…_initstate_0` name | **Native** — env moves `agentview` from the name; just record `agentview_image` ✅ | **Hook**: re-apply the same params to frontview+sideview by reusing the fork's geometry helpers (`rotate_around_z`/`rotate_around_y`/`scale_distance_from_pivot` in `problems/*.py`) via `mujoco_arena.set_camera` / `CameraModder` |
| **Sensor noise** | **Sampled** corruption+severity, formatted into `_noise_<m>` (m: 1–10 motion, 11–20 gaussian, 21–30 zoom, 31–40 fog, 41–50 glass) | **Native** — env blurs `agentview_image`; just record it ✅ | **Hook**: import the fork's kernels (`motion_blur`/`gaussian_blur`/`zoom_blur`/`fog`/`glass_blur` from `env_wrapper.py`) and apply post-render to frontview/sideview |

"Exact" = reuse the fork's perturbation *code + assets*: literal bddl reuse for **light + texture**; for
camera/noise the fork's transform + blur code is reused (native on agentview, re-applied to the extra
views). Per the user, instances are **sampled** (the plan's original sizing), NOT pulled from the eval
`task_classification.json`.

### Reused building blocks (do not rewrite)
- **Fork's native perturbation (default cams):** `LIBERO-plus/.../envs/env_wrapper.py` `ControlEnv` parses
  the task name and applies camera (via `problems/*.py:_setup_camera`) + noise (post-render blur) to
  `agentview`. Drive it by synthesizing the perturbed task name — no `CameraModder`/cv2 of our own.
- **Fork's reusable functions (additional cams):** geometry helpers `rotate_around_z`, `rotate_around_y`,
  `scale_distance_from_pivot` (in each `problems/*.py`) for the camera transform; blur kernels
  `motion_blur`, `gaussian_blur`, `zoom_blur`, `fog`, `glass_blur` (in `env_wrapper.py`) for noise.
  Import these and re-apply to frontview/sideview; `CameraModder` from robosuite `utils/mjmod.py` is a
  fallback only if `set_camera` re-application is awkward.
- Existing replay/init in `regenerate_libero_dataset.py`: `drive_to_start_and_splice`, `is_noop`,
  `set_controller_absolute`, `get_eef_goal_action`, success/failure HDF5 split.
- `custom_robots/` (incl. Sawyer vendored-XML symlink) — import into the fork env. **NOTE:** fork pins
  **robosuite==1.4.0** (not 1.4.1) and base problems wrap robots as **`Mounted{robot}`**
  (`problems/*.py:136` etc.), so cross-embodiment needs `MountedUR5e`/`MountedKinova3`/… registered —
  verify `custom_robots` covers this in the fork env (smoke-test early).
- Conversion: `config.py:get_libero_features`, `libero_utils.py:load_local_episodes`, `libero_h5.py`.
- **`vpro_mimicgen_eval/data_regen/run_generation_parallel.sh`** — the parallel-runner template (below).

### Parallel runner (mirror vpro_mimicgen_eval)
Replace the phased `run_all_embodiments.sh` with a **manifest + `xargs -P CONCURRENCY` pool**, each
line one combo = `robot × dim × suite`:
- Worker does regen → convert → **delete raw** end-to-end; one **self-contained per-combo LeRobot
  dataset** (matches "per-dimension" output) pushed to `OliverHausdoerfer/libero_plus_<dim>_<suite>_<robot>_additionalCams` (+ `_failures`).
- **Resumable**: skip combos whose `meta/info.json` exists.
- **Disk safety**: up-front preflight (`WORKERS × PER_COMBO_GB`) + per-worker `MIN_FREE_GB` guard;
  CONCURRENCY + PER_COMBO_GB are the safety knobs (keep their stability-critical treatment).
- **Camera-set env toggle** (`--cameras additional` ↔ a `CAMERA_SET` env) writing to a parallel output
  tree, exactly like `MG_CAMERA_SET`.
- Per-combo yield CSV (flock-upsert), START/DONE/skip to stdout.

## Files to create / modify

**Env setup (one-time, manual):** the fork is already cloned at repo-root `LIBERO-plus/` (code, depth-1,
robosuite==1.4.0/bddl==1.0.1). Create conda env `libero_plus` (`pip install -e LIBERO-plus`, which removes
vanilla `libero`), place the **`assets/`** tree at `LIBERO-plus/libero/libero/assets/` (needed only for
light/texture), and make `custom_robots` importable (register the `Mounted{robot}` variants).
**Assets gotcha (verified):** the downloaded `assets.zip` (at `LIBERO-plus/_assets_dl/assets.zip`, 6.4 GB,
457,675 entries) bakes in the author's absolute path — the real `assets/` sits at
`inspire/hdd/project/embodied-multimodality/public/syfei/libero_new/release/dataset/LIBERO-plus-0/assets/`.
So do NOT `unzip -d libero/libero` blindly; extract that nested `…/LIBERO-plus-0/assets` subtree and move
it to `libero/libero/assets/` (e.g. `unzip` then `mv …/LIBERO-plus-0/assets libero/libero/`).

**New:**
- `regenerate_libero_plus_dataset.py` — **new, standalone** LIBERO-Plus regenerator. Holds ALL
  `--libero_plus`-only flags (`--perturbation_dim {camera,lighting,texture,noise}`, `--include-mix`,
  `--cap-per-dim`) and the perturbation work-item outer loop. **Imports** the pure replay/init helpers
  from `regenerate_libero_dataset.py` (`drive_to_start_and_splice`, `is_noop`, `set_controller_absolute`,
  `get_eef_goal_action`, `get_libero_dummy_action`, `get_source_panda_env`, `get_libero_env`,
  `ROBOT_JOINT_DIMS`) and the `CAMERA_SETS` registry from `config.py`. Reuses the same `--cameras`
  mechanism. Adds the per-dimension perturbation:
  - **light/texture** = instantiate the perturbed bddl (needs `assets.zip`);
  - **camera/noise** = sample params, **synthesize the perturbed task name** (`…_view_…_initstate_0`
    [`_noise_<m>`]) so the fork applies it natively to `agentview` for default cams; for additional cams,
    re-apply the SAME params to frontview/sideview using the fork's reused helpers/kernels;
  and logs `{dim, source_id, instance, params}` into HDF5 attrs. Per the user's constraint, the ~80-line
  replay+save inner loop is intentionally **copied** here (adapted to apply the perturbation) rather than
  extracted, to keep `regenerate_libero_dataset.py` untouched beyond the camera change.
- `libero_utils/libero_plus_tasks.py` — for a (suite, dim): enumerate perturbation work items —
  light → `_light_` bddl files; texture → `_table_`/`_tb_` bddl files; camera/noise → **sampled params**
  (the plan's ranges; NOT the eval `task_classification.json`, per user) — honoring
  `--include-mix`/`--cap-per-dim`, pair each with its base-task original demo in
  `libero_datasets/<suite>/` (base name = strip the perturbation suffix), and yield the work items.
- `libero_utils/sensor_noise.py` — **thin wrapper that imports the fork's blur kernels** (`motion_blur`,
  `gaussian_blur`, `zoom_blur`, `fog`, `glass_blur` from `LIBERO-plus/.../env_wrapper.py`) and applies the
  sampled corruption to the additional views; do NOT re-implement kernels. (Default cams get noise from
  the fork natively.)
- `run_libero_plus_parallel.sh` — the manifest + `xargs -P` runner above (port from vpro template).
- `gen_libero_plus_manifest.py` — emit the combo manifest (robot × dim × suite × num_instances).

**Modify:**
- `regenerate_libero_dataset.py` — **ONLY** the dynamic-camera change (no `--libero_plus`, no
  perturbation logic — that all lives in the new Plus script):
  - add `--cameras {default,additional}` (default `default`);
  - `get_libero_env(task, robot, resolution, cameras)` → `camera_names = [c[0] for c in CAMERA_SETS[cameras]]`;
  - replace the five hardcoded/commented image blocks in `main` with loops over `CAMERA_SETS[args.cameras]`:
    collect per-cam frames into a dict keyed by `hdf5_rgb_key` (reading `obs[env_obs_image_key][::-1, ::-1]`),
    then `obs_grp.create_dataset(hdf5_rgb_key, ...)` for each entry. Delete the commented
    frontview/birdview/sideview lines.
- `config.py` — add `CAMERA_SETS`; make `get_libero_features(robot_type, cameras="default")` build the
  image features from `CAMERA_SETS[cameras]` (delete the commented blocks); keep `LIBERO_FEATURES` as the
  `"default"` instantiation for back-compat. Keep robot joint dims.
- `libero_utils.py` — `load_local_episodes(input_h5, cameras="default")` builds the episode image entries
  from `CAMERA_SETS[cameras]` (`lerobot_feature_key ← demo["obs/"+hdf5_rgb_key]`); delete the commented blocks.
- `libero_h5.py` — add `--cameras {default,additional}`; thread it through `SaveLerobotDataset` into both
  `get_libero_features(...)` and `load_local_episodes(...)` so the converted dataset's features and frames
  match the regenerated camera set.
- `run_all_embodiments.sh` (standard "switch-back" path) — replace the hand-set `CAMSUFFIX` with a
  `CAMERAS` var (`default`|`additional`); derive `CAMSUFFIX` from it (`_${CAMERAS}Cams` or an explicit
  map); pass `--cameras "$CAMERAS"` to both `regen` (`regenerate_libero_dataset.py`) and `convert_push`
  (`libero_h5.py`). No more editing source to switch cameras.

## Scope / scale
- Matrix: 4 dims × **4 suites (no libero_90)** × **5 embodiments (Panda + UR5e/Kinova3/IIWA/Sawyer)** ×
  **2 cam sets (one at a time)**, replicating LIBERO-Plus's **full per-dim instance set incl.
  `libero_mix`** (~4,000/dim/robot) → ~16k trajs per (robot, cam set). Meets/exceeds the published 14,347.
- **Order: generate the eval-conformant core first** — Panda × default cams × 4 dims — then the
  auxiliary passes (non-Panda; front+sideview) as separate runs (`--cameras` selects one set per run).
- ~2× a standard cross-embodiment LIBERO run per dimension (full instance set), so the parallel runner +
  disk gating is essential. `--cap-per-dim` to subsample for pilots/disk pressure.

## Verification
1. **Camera/noise spike** (the params location is now RESOLVED — they're in the task name, applied
   natively to `agentview`): (a) confirm a synthesized `…_view_…_initstate_0` name moves agentview and a
   `…_noise_<m>` name blurs `agentview_image` (default cams, no custom code); (b) confirm the
   additional-cam hook re-applies the SAME params to frontview/sideview and produces an equivalent
   perturbation magnitude (reusing the fork's transform helpers + blur kernels). Robot-init/language/
   objects dims are out of scope; texture is bddl-backed `_table_`/`_tb_`.
2. **Smoke** (fork env): `regenerate_libero_plus_dataset.py --perturbation_dim lighting --robot IIWA
   --cameras additional --max_demos_per_task 2 --libero_task_suite libero_object`. Verify env builds,
   IIWA acts, frontview+sideview render, lighting visibly varies across instances, sane success rate,
   HDF5 logs.
3. **Convert + inspect**: `libero_h5.py --robot-type iiwa --cameras additional`; confirm 2 image
   features, joint dim 7, dim tag.
4. Repeat per dim (lighting → noise → texture → camera per spike results).
5. **Eval-key alignment**: confirm the LIBERO-Plus eval can be configured to map env agentview/wrist →
   our dataset keys (`observation.images.image` + `observation.images.wrist_image`); pin this before
   training so the Panda+default datasets feed the policy correctly.
6. **Switch-back**: in `any4lerobot`, run `regenerate_libero_dataset.py --cameras additional` (no
   `--libero_plus` flag exists anymore) + `libero_h5.py --cameras additional`, via
   `run_all_embodiments.sh` with `CAMERAS=additional`, on libero_object/IIWA; confirm parity with prior
   `_additionalCams` output, and `CAMERAS=default` parity with current `_defaultCams`.
   **Camera-parity guard:** `--cameras default` must reproduce the exact HDF5 keys, feature keys, and
   repo names produced today (regression check for the toggle→flag refactor).
7. **Parallel runner**: dry-run the manifest + a 2-combo live run with disk preflight, resumability
   (re-run skips finished combos). Then scale **eval-conformant core first** (Panda × default × 4 dims),
   one dimension at a time, detached/monitored; auxiliary passes after.

## Decisions (confirmed with user)
- **Eval = standard LIBERO-Plus only** (Panda, agentview+wrist, 7 dims). Eval-conformant core =
  Panda × default cams × 4 dims (generate first); non-Panda + front/sideview are auxiliary.
- **Cameras: both sets, one at a time** via `--cameras {default,additional}`; front/sideview perturbed
  as discussed.
- **Dims: keep the 4 render dims** (camera, light, texture, noise). No language; physics dims untrainable.
- **Scope: drop libero_90**; **include `libero_mix`** (additional single-dim instances, ~half the data).
- **Size: match the original** → full per-dimension instance set (~4,000/dim/robot). **Sample params
  for camera/noise** (do NOT enumerate from the eval `task_classification.json`) — confirmed 2026-06-23.
- **Camera/noise on BOTH cam sets** — confirmed 2026-06-23: the native fork mechanism only perturbs
  `agentview`/`agentview_image`, so the additional cam set (frontview+sideview) gets an explicit
  re-application hook (reusing the fork's transform helpers + blur kernels). The user explicitly wants
  these perturbations on frontview+sideview, not just the default cam.
- **No `CameraModder`/custom cv2 needed for default cams** — confirmed 2026-06-23 by inspecting the clone:
  camera+noise+robot-init are applied natively from the task name (`env_wrapper.py`); synthesize the name.
- **`assets.zip` downloaded** (2026-06-23) to `LIBERO-plus/_assets_dl/`; unzip into `libero/libero/` for
  light/texture.
- One perturbation dimension per trajectory — never combined (confirmed via eval taxonomy).
