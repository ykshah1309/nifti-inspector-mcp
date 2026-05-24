"""Implementations of the four MCP tools.

These functions accept Pydantic input models and return Pydantic output models.
The MCP server layer (server.py) wraps them and handles JSON-RPC plumbing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import nibabel as nib
import numpy as np

from .models import (
    BIDSDatasetSummary,
    CheckMotionInput,
    LoadNIfTIInput,
    MotionReport,
    NIfTIMetadata,
    SummarizeBIDSInput,
    ValidateBIDSInput,
    ValidationReport,
)


# Map nibabel intent codes back to their canonical names. Newer nibabel exposes
# this via header.get_intent(); we keep a small dict for resilience.
_INTENT_NAMES = {
    0: "NIFTI_INTENT_NONE",
    2: "NIFTI_INTENT_CORREL",
    3: "NIFTI_INTENT_TTEST",
    4: "NIFTI_INTENT_FTEST",
    5: "NIFTI_INTENT_ZSCORE",
    6: "NIFTI_INTENT_CHISQ",
    7: "NIFTI_INTENT_BETA",
    1001: "NIFTI_INTENT_ESTIMATE",
    1002: "NIFTI_INTENT_LABEL",
    1007: "NIFTI_INTENT_VECTOR",
    1009: "NIFTI_INTENT_TRIANGLE",
    2001: "NIFTI_INTENT_NORMAL",
}


def _intent_name(code: int) -> str:
    return _INTENT_NAMES.get(int(code), f"NIFTI_INTENT_UNKNOWN({int(code)})")


# ---------- Tool 1: load_nifti ----------

def load_nifti(params: LoadNIfTIInput) -> NIfTIMetadata:
    """Load a NIfTI file and return its header metadata."""
    path = Path(params.path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"NIfTI file not found: {path}")

    img = nib.load(str(path))
    header = img.header
    shape = list(img.shape)
    zooms = [float(z) for z in header.get_zooms()]

    spatial_units, temporal_units = header.get_xyzt_units()
    units = {"spatial": str(spatial_units), "temporal": str(temporal_units)}

    num_volumes = int(shape[3]) if len(shape) >= 4 else 1

    intent_code_int = int(header["intent_code"])

    return NIfTIMetadata(
        filename=path.name,
        dimensions=shape,
        voxel_size_mm=zooms,
        datatype=str(np.dtype(header.get_data_dtype())),
        num_volumes=num_volumes,
        affine_matrix=[[float(x) for x in row] for row in img.affine],
        units=units,
        intent_code=_intent_name(intent_code_int),
    )


# ---------- Tool 2: check_motion ----------

def _center_of_mass(volume: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """Intensity-weighted center of mass in world (mm) coordinates."""
    # Use absolute intensities so negative values (rare in raw fMRI but
    # possible after preprocessing) don't cancel out the weighting.
    weights = np.abs(volume).astype(np.float64)
    total = weights.sum()
    if total <= 0:
        # Degenerate volume — fall back to the geometric center.
        idx = np.array(volume.shape) / 2.0
    else:
        grids = np.indices(volume.shape, dtype=np.float64)
        idx = np.array([(g * weights).sum() / total for g in grids])
    voxel_coord = np.append(idx, 1.0)
    world = affine @ voxel_coord
    return world[:3]


def check_motion(params: CheckMotionInput) -> MotionReport:
    """Estimate frame-to-frame motion via center-of-mass displacement.

    Why: a real motion estimate needs FSL MCFLIRT or similar rigid-body
    registration. For a lightweight demo we use COM shifts as a directional
    proxy — it flags gross motion reliably and needs no external binary.
    """
    path = Path(params.path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"NIfTI file not found: {path}")

    img = nib.load(str(path))
    shape = img.shape
    if len(shape) < 4 or shape[3] < 2:
        raise ValueError(
            f"Motion analysis requires 4D data with >=2 volumes; got shape {shape}. "
            "Pass a 4D fMRI run (typically *_bold.nii.gz)."
        )

    data = img.get_fdata(dtype=np.float32)
    affine = img.affine
    n_vols = data.shape[3]

    coms = np.array([_center_of_mass(data[..., t], affine) for t in range(n_vols)])
    diffs = np.linalg.norm(np.diff(coms, axis=0), axis=1)  # length n_vols - 1
    # Pad so displacement[i] corresponds to volume i (vol 0 has no predecessor).
    displacements = np.concatenate([[0.0], diffs])

    flagged = [int(i) for i, d in enumerate(displacements) if d > params.threshold_mm]

    return MotionReport(
        total_volumes=int(n_vols),
        flagged_volumes=flagged,
        max_displacement_mm=float(displacements.max()),
        mean_displacement_mm=float(displacements.mean()),
        flagged_count=len(flagged),
        threshold_used_mm=float(params.threshold_mm),
    )


# ---------- Tool 3: summarize_bids ----------

def summarize_bids(params: SummarizeBIDSInput) -> BIDSDatasetSummary:
    """Summarize a BIDS dataset using pybids' BIDSLayout."""
    from bids import BIDSLayout  # imported lazily — pybids import is slow

    root = Path(params.bids_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"BIDS root not found or not a directory: {root}")

    layout = BIDSLayout(str(root), validate=False)
    subjects = sorted(layout.get_subjects())
    sessions = sorted(layout.get_sessions())
    modalities = sorted({d for d in layout.get_datatypes()})
    tasks = sorted(layout.get_tasks())
    total_scans = len(layout.get(extension=[".nii", ".nii.gz"]))
    has_derivatives = (root / "derivatives").is_dir()

    return BIDSDatasetSummary(
        dataset_path=str(root),
        num_subjects=len(subjects),
        subjects=[f"sub-{s}" for s in subjects],
        num_sessions=len(sessions),
        modalities=modalities,
        total_scans=total_scans,
        task_names=tasks,
        has_derivatives=has_derivatives,
    )


# ---------- Tool 4: validate_bids ----------

def _basic_bids_check(root: Path) -> ValidationReport:
    """Lightweight fallback when the bids-validator CLI isn't installed."""
    errors: list[str] = []
    warnings: list[str] = []

    desc = root / "dataset_description.json"
    if not desc.is_file():
        errors.append("Missing required file: dataset_description.json at dataset root.")
    else:
        try:
            with open(desc, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            for key in ("Name", "BIDSVersion"):
                if key not in meta:
                    warnings.append(f"dataset_description.json is missing recommended key '{key}'.")
        except json.JSONDecodeError as exc:
            errors.append(f"dataset_description.json is not valid JSON: {exc}")

    subject_dirs = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("sub-"))
    if not subject_dirs:
        errors.append("No sub-XX/ directories found at dataset root.")

    known_modalities = {"anat", "func", "dwi", "fmap", "perf", "meg", "eeg", "ieeg", "pet"}
    for sub in subject_dirs:
        # Allow either sub-XX/<modality>/ or sub-XX/ses-YY/<modality>/.
        modality_dirs: list[Path] = []
        for child in sub.iterdir():
            if not child.is_dir():
                continue
            if child.name.startswith("ses-"):
                modality_dirs.extend(c for c in child.iterdir() if c.is_dir())
            else:
                modality_dirs.append(child)
        if not modality_dirs:
            errors.append(f"{sub.name}: no modality subdirectories found.")
            continue
        unknown = [d.name for d in modality_dirs if d.name not in known_modalities]
        if unknown:
            warnings.append(f"{sub.name}: unrecognized modality directories: {unknown}")

    if (root / "participants.tsv").is_file() is False:
        warnings.append("Optional file participants.tsv not present at root.")

    is_valid = not errors
    summary = (
        "Basic Python BIDS structure check (not the full bids-validator). "
        f"Found {len(subject_dirs)} subject directory/directories, "
        f"{len(errors)} error(s), {len(warnings)} warning(s)."
    )
    return ValidationReport(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        summary=summary,
    )


def _run_bids_validator_cli(root: Path) -> ValidationReport | None:
    """Run the official bids-validator CLI if installed. Returns None if absent."""
    exe = shutil.which("bids-validator")
    if exe is None:
        return None
    try:
        proc = subprocess.run(
            [exe, str(root), "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ValidationReport(
            is_valid=False,
            errors=[f"bids-validator failed to run: {exc}"],
            warnings=[],
            summary="bids-validator CLI could not be invoked.",
        )

    raw = proc.stdout.strip() or proc.stderr.strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return ValidationReport(
            is_valid=proc.returncode == 0,
            errors=[] if proc.returncode == 0 else [raw[:2000] or "validator returned non-zero exit"],
            warnings=[],
            summary="bids-validator CLI output was not JSON; surfacing raw text.",
        )

    issues = payload.get("issues") or {}
    err_list = issues.get("errors") or []
    warn_list = issues.get("warnings") or []

    def _flatten(items: list) -> list[str]:
        out: list[str] = []
        for it in items:
            if isinstance(it, dict):
                key = it.get("key") or it.get("code") or "issue"
                reason = it.get("reason") or it.get("description") or ""
                out.append(f"{key}: {reason}".strip(": ").strip())
            else:
                out.append(str(it))
        return out

    errors = _flatten(err_list)
    warnings = _flatten(warn_list)
    is_valid = not errors and proc.returncode == 0
    summary = (
        f"bids-validator CLI v{payload.get('version', 'unknown')}: "
        f"{len(errors)} error(s), {len(warnings)} warning(s)."
    )
    return ValidationReport(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        summary=summary,
    )


def validate_bids(params: ValidateBIDSInput) -> ValidationReport:
    """Validate a BIDS dataset. Prefers the official CLI; falls back to a basic check."""
    root = Path(params.bids_root).expanduser().resolve()
    if not root.is_dir():
        return ValidationReport(
            is_valid=False,
            errors=[f"BIDS root not found or not a directory: {root}"],
            warnings=[],
            summary="Validation aborted: input path is not a directory.",
        )

    cli_report = _run_bids_validator_cli(root)
    if cli_report is not None:
        return cli_report
    return _basic_bids_check(root)
