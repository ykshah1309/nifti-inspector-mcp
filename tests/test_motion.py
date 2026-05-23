"""Smoke tests for check_motion."""

from __future__ import annotations

from pathlib import Path

import pytest

from nifti_inspector.models import CheckMotionInput
from nifti_inspector.tools import check_motion

from .generate_sample_data import MOTION_FLAGGED_VOLUMES, generate

SAMPLE = Path(__file__).resolve().parent / "sample_data"
BOLD = SAMPLE / "sub-01_task-rest_bold.nii.gz"
T1 = SAMPLE / "sub-01_T1w.nii.gz"


@pytest.fixture(scope="module", autouse=True)
def _ensure_sample_data():
    if not BOLD.exists() or not T1.exists():
        generate(force=False)


def test_check_motion_flags_intentional_displacements():
    report = check_motion(CheckMotionInput(path=str(BOLD), threshold_mm=2.0))
    assert report.total_volumes == 20
    assert report.threshold_used_mm == 2.0
    for vol_idx in MOTION_FLAGGED_VOLUMES:
        assert vol_idx in report.flagged_volumes, (
            f"Expected volume {vol_idx} to be flagged; got {report.flagged_volumes}"
        )
    assert report.flagged_count >= len(MOTION_FLAGGED_VOLUMES)
    assert report.max_displacement_mm > 2.0


def test_check_motion_rejects_3d_input():
    with pytest.raises(ValueError, match="4D"):
        check_motion(CheckMotionInput(path=str(T1)))
