"""Smoke tests for summarize_bids and validate_bids."""

from __future__ import annotations

from pathlib import Path

import pytest

from nifti_inspector.models import SummarizeBIDSInput, ValidateBIDSInput
from nifti_inspector.tools import summarize_bids, validate_bids

from .generate_sample_data import generate

SAMPLE = Path(__file__).resolve().parent / "sample_data"
BIDS = SAMPLE / "bids_demo"


@pytest.fixture(scope="module", autouse=True)
def _ensure_sample_data():
    if not (BIDS / "dataset_description.json").exists():
        generate(force=False)


def test_summarize_bids_reports_two_subjects_and_modalities():
    summary = summarize_bids(SummarizeBIDSInput(bids_root=str(BIDS)))
    assert summary.num_subjects == 2
    assert set(summary.subjects) == {"sub-01", "sub-02"}
    assert "anat" in summary.modalities
    assert "func" in summary.modalities
    assert "rest" in summary.task_names
    assert summary.total_scans >= 3  # 2 T1w + 1 bold
    assert summary.has_derivatives is False


def test_validate_bids_basic_check_passes_for_demo_dataset():
    report = validate_bids(ValidateBIDSInput(bids_root=str(BIDS)))
    # Errors should be empty for our synthetic dataset (whether the official
    # CLI is installed or we fall back to the basic check).
    assert report.is_valid is True, f"validation errors: {report.errors}"
    assert isinstance(report.warnings, list)
    assert report.summary
