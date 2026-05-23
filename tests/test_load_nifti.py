"""Smoke tests for load_nifti."""

from __future__ import annotations

from pathlib import Path

import pytest

from nifti_inspector.models import LoadNIfTIInput
from nifti_inspector.tools import load_nifti

from .generate_sample_data import generate

SAMPLE = Path(__file__).resolve().parent / "sample_data"
T1 = SAMPLE / "sub-01_T1w.nii.gz"


@pytest.fixture(scope="module", autouse=True)
def _ensure_sample_data():
    if not T1.exists():
        generate(force=False)


def test_load_nifti_returns_expected_shape_and_voxel_size():
    md = load_nifti(LoadNIfTIInput(path=str(T1)))
    assert md.filename == "sub-01_T1w.nii.gz"
    assert md.dimensions == [32, 32, 16]
    assert md.voxel_size_mm == [1.0, 1.0, 1.0]
    assert md.num_volumes == 1
    assert md.datatype == "float32"
    assert len(md.affine_matrix) == 4
    assert len(md.affine_matrix[0]) == 4
    assert md.units["spatial"] == "mm"


def test_load_nifti_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_nifti(LoadNIfTIInput(path=str(SAMPLE / "does_not_exist.nii.gz")))
