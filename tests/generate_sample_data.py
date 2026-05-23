"""Generate synthetic NIfTI files and a minimal BIDS layout for tests/demo.

Run once after `pip install -e .`:
    python tests/generate_sample_data.py

Idempotent: skips files that already exist. Re-run with --force to overwrite.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import nibabel as nib
import numpy as np

HERE = Path(__file__).resolve().parent
SAMPLE = HERE / "sample_data"
BIDS = SAMPLE / "bids_demo"

# Volumes intentionally shifted so check_motion has obvious targets.
MOTION_FLAGGED_VOLUMES = (8, 15)


def _save_t1w(path: Path, force: bool) -> None:
    if path.exists() and not force:
        print(f"[skip] {path}")
        return
    rng = np.random.default_rng(seed=42)
    data = rng.standard_normal((32, 32, 16)).astype(np.float32)
    affine = np.diag([1.0, 1.0, 1.0, 1.0])
    img = nib.Nifti1Image(data, affine)
    img.header.set_xyzt_units(xyz="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(img, str(path))
    print(f"[write] {path}  shape={data.shape} dtype={data.dtype}")


def _save_bold(path: Path, force: bool) -> None:
    if path.exists() and not force:
        print(f"[skip] {path}")
        return
    rng = np.random.default_rng(seed=7)
    nx, ny, nz, nt = 32, 32, 16, 20

    # Build a base brain-shaped blob in the center so center-of-mass is stable.
    zz, yy, xx = np.indices((nz, ny, nx), dtype=np.float32)
    cz, cy, cx = nz / 2.0, ny / 2.0, nx / 2.0
    blob = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2) / (2 * 6.0 ** 2)))
    blob = np.transpose(blob, (2, 1, 0))  # (x, y, z)

    data = np.empty((nx, ny, nz, nt), dtype=np.float32)
    for t in range(nt):
        noise = rng.standard_normal((nx, ny, nz)).astype(np.float32) * 0.05
        vol = blob + noise
        if t in MOTION_FLAGGED_VOLUMES:
            # Apply a hefty spatial shift along x to spike COM displacement.
            shift = 6  # voxels (~18 mm at 3 mm isotropic) — well above 2.0 mm threshold
            shifted = np.zeros_like(vol)
            shifted[shift:, :, :] = vol[:-shift, :, :]
            vol = shifted
        data[..., t] = vol

    affine = np.diag([3.0, 3.0, 3.0, 1.0])  # 3 mm isotropic voxels
    img = nib.Nifti1Image(data, affine)
    img.header.set_xyzt_units(xyz="mm", t="sec")
    img.header["pixdim"][4] = 2.0  # TR = 2 s
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(img, str(path))
    print(f"[write] {path}  shape={data.shape} dtype={data.dtype}  shifted_at={MOTION_FLAGGED_VOLUMES}")


def _write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"[skip] {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[write] {path}")


def _copy(src: Path, dst: Path, force: bool) -> None:
    if dst.exists() and not force:
        print(f"[skip] {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"[copy ] {src.name} -> {dst}")


def generate(force: bool = False) -> None:
    SAMPLE.mkdir(parents=True, exist_ok=True)

    # Standalone synthetic files (also used as BIDS sources).
    t1_src = SAMPLE / "sub-01_T1w.nii.gz"
    bold_src = SAMPLE / "sub-01_task-rest_bold.nii.gz"
    _save_t1w(t1_src, force)
    _save_bold(bold_src, force)

    # BIDS layout.
    _write_text(
        BIDS / "dataset_description.json",
        json.dumps(
            {
                "Name": "nifti-inspector-mcp demo dataset",
                "BIDSVersion": "1.8.0",
                "DatasetType": "raw",
                "Authors": ["Yash Kamlesh Shah"],
            },
            indent=2,
        ),
        force,
    )
    _write_text(
        BIDS / "README",
        "Synthetic BIDS dataset generated for nifti-inspector-mcp demo and tests.\n",
        force,
    )
    _write_text(
        BIDS / "participants.tsv",
        "participant_id\tage\tsex\nsub-01\t27\tM\nsub-02\t31\tF\n",
        force,
    )

    # sub-01: T1w + rest BOLD
    _copy(t1_src, BIDS / "sub-01" / "anat" / "sub-01_T1w.nii.gz", force)
    _copy(bold_src, BIDS / "sub-01" / "func" / "sub-01_task-rest_bold.nii.gz", force)
    _write_text(
        BIDS / "sub-01" / "func" / "sub-01_task-rest_bold.json",
        json.dumps({"TaskName": "rest", "RepetitionTime": 2.0}, indent=2),
        force,
    )

    # sub-02: T1w only
    _copy(t1_src, BIDS / "sub-02" / "anat" / "sub-02_T1w.nii.gz", force)

    print("\nDone. Sample data in:", SAMPLE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()
    generate(force=args.force)
