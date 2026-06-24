"""Enumerate LIBERO-Plus perturbation work items for a (suite, dimension).

A *work item* is one regeneration unit: a perturbed scene paired with one original Panda demo
trajectory. The four render dimensions enumerate differently:

  - light / texture : the perturbation is a real bddl FILE shipped by the fork
    (`<base>_light_<n>.bddl`, `<base>_table_<n>.bddl`, `<base>_tb_<n>.bddl`). Instance `n`
    pairs with `demo_<n-1>` of the base task (the fork generated them 1:1 with the demos).
  - camera / noise : NO bddl files exist; the perturbation is sampled parameters. We iterate
    every demo of every base task and draw `--include-mix ? 2 : 1` parameter set(s) per demo.

The base task name (strip the perturbation suffix) maps to the original demo at
`<libero_raw_data_root>/<suite>/<base>_demo.hdf5` and the base bddl at
`<bddl_root>/<suite>/<base>.bddl`.
"""

import random
from collections import namedtuple
from pathlib import Path

import h5py

# Token sets per dimension. Camera/noise have none (sampled, not file-backed).
TEXTURE_TOKENS = ("table", "tb")
LIGHT_TOKENS = ("light",)

# Sampling ranges for camera viewpoint (mirrors the paper's perturbation envelope; the user
# chose sampled params over enumerating the eval task_classification.json).
CAMERA_RANGES = {
    "horizon_deg": (15, 75),  # azimuth cone, sign randomised
    "vertical_deg": (0, 40),  # elevation cone, sign randomised
    "scale": (1.01, 2.0),  # distance-from-pivot factor
    "endpoint_rot_deg": (2, 10),  # in-place roll, sign randomised
    "endpoint_vert_deg": (2, 10),  # in-place pitch, sign randomised
}

# dim -> (bddl_path, params); params is None for light/texture, the view tuple for camera,
# an int severity for noise.
WorkItem = namedtuple("WorkItem", ["dim", "base_task", "base_suite", "demo_index", "bddl_path", "params"])


def _strip_token(stem: str, token: str):
    """If stem ends with `_<token>_<n>`, return (base, n) else None."""
    marker = f"_{token}_"
    idx = stem.rfind(marker)
    if idx == -1:
        return None
    suffix = stem[idx + len(marker) :]
    if not suffix.isdigit():
        return None
    return stem[:idx], int(suffix)


def build_demo_index(libero_raw_data_root: Path, suites) -> dict:
    """base_task -> (suite, demo_path) across all base suites (for cross-suite mix resolution)."""
    index = {}
    for suite in suites:
        suite_dir = libero_raw_data_root / suite
        if not suite_dir.is_dir():
            continue
        for demo in suite_dir.glob("*_demo.hdf5"):
            base = demo.name[: -len("_demo.hdf5")]
            index[base] = (suite, demo)
    return index


def _file_backed_items(dim, tokens, bddl_root, suite, demo_index, include_mix):
    """Enumerate light/texture work items from the bddl files in a suite (+ mix) folder.

    `libero_mix` is cross-suite, so we only keep mix instances whose base task lives in the
    current suite — each base task is processed exactly once, under its own suite combo. With
    mix on this gives ~2 perturbations/demo (per-suite + mix), matching the published ~4,000/dim.
    """
    folders = [suite] + (["libero_mix"] if include_mix else [])
    seen = set()
    for folder in folders:
        folder_dir = bddl_root / folder
        if not folder_dir.is_dir():
            continue
        for token in tokens:
            for bddl in sorted(folder_dir.glob(f"*_{token}_*.bddl")):
                parsed = _strip_token(bddl.stem, token)
                if parsed is None:
                    continue
                base, n = parsed
                if base not in demo_index:
                    continue  # perturbed scene with no matching base demo
                base_suite, _ = demo_index[base]
                if base_suite != suite:
                    continue  # mix instance whose base task belongs to a different suite
                key = (base, folder, token, n)
                if key in seen:
                    continue
                seen.add(key)
                yield WorkItem(dim, base, base_suite, n - 1, str(bddl), None)


def _sample_camera_params(rng):
    r = CAMERA_RANGES
    sign = lambda: rng.choice((-1, 1))  # noqa: E731
    return (
        sign() * rng.randint(*r["horizon_deg"]),
        sign() * rng.randint(*r["vertical_deg"]),
        round(rng.uniform(*r["scale"]), 2),
        sign() * rng.randint(*r["endpoint_rot_deg"]),
        sign() * rng.randint(*r["endpoint_vert_deg"]),
    )


def _sampled_items(dim, bddl_root, suite, libero_raw_data_root, num_samples, max_demos, rng):
    """Enumerate camera/noise work items: one base bddl + sampled params per demo."""
    suite_dir = libero_raw_data_root / suite
    for demo in sorted(suite_dir.glob("*_demo.hdf5")):
        base = demo.name[: -len("_demo.hdf5")]
        base_bddl = bddl_root / suite / f"{base}.bddl"
        if not base_bddl.exists():
            continue
        with h5py.File(demo, "r") as f:
            num_demos = len(f["data"].keys())
        if max_demos is not None:
            num_demos = min(num_demos, max_demos)
        for demo_index in range(num_demos):
            for _ in range(num_samples):
                if dim == "camera":
                    params = _sample_camera_params(rng)
                else:  # noise
                    params = rng.randint(1, 50)
                yield WorkItem(dim, base, suite, demo_index, str(base_bddl), params)


def enumerate_work_items(
    dim: str,
    suite: str,
    bddl_root: Path,
    libero_raw_data_root: Path,
    suites,
    include_mix: bool = True,
    cap_per_dim: int = None,
    max_demos: int = None,
    seed: int = 0,
):
    """Return a list of WorkItem for one (dim, suite). `suites` is all base suites (for mix)."""
    bddl_root = Path(bddl_root)
    libero_raw_data_root = Path(libero_raw_data_root)
    demo_index = build_demo_index(libero_raw_data_root, suites)
    rng = random.Random(seed)

    if dim == "lighting":
        items = list(_file_backed_items("lighting", LIGHT_TOKENS, bddl_root, suite, demo_index, include_mix))
    elif dim == "texture":
        items = list(_file_backed_items("texture", TEXTURE_TOKENS, bddl_root, suite, demo_index, include_mix))
    elif dim in ("camera", "noise"):
        num_samples = 2 if include_mix else 1
        items = list(_sampled_items(dim, bddl_root, suite, libero_raw_data_root, num_samples, max_demos, rng))
    else:
        raise ValueError(f"unknown perturbation dim: {dim}")

    if cap_per_dim is not None and len(items) > cap_per_dim:
        items = rng.sample(items, cap_per_dim)
    return items
