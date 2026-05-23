"""Pydantic models for typed tool inputs and outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------- Tool 1: load_nifti ----------

class LoadNIfTIInput(BaseModel):
    path: str = Field(description="Absolute or relative path to a .nii or .nii.gz file")


class NIfTIMetadata(BaseModel):
    filename: str
    dimensions: list[int]
    voxel_size_mm: list[float]
    datatype: str
    num_volumes: int
    affine_matrix: list[list[float]]
    units: dict[str, str]
    intent_code: str


# ---------- Tool 2: check_motion ----------

class CheckMotionInput(BaseModel):
    path: str = Field(description="Path to a 4D .nii.gz file (typically fMRI)")
    threshold_mm: float = Field(
        default=2.0,
        description="Frame-to-frame displacement threshold in mm",
    )


class MotionReport(BaseModel):
    total_volumes: int
    flagged_volumes: list[int]
    max_displacement_mm: float
    mean_displacement_mm: float
    flagged_count: int
    threshold_used_mm: float


# ---------- Tool 3: summarize_bids ----------

class SummarizeBIDSInput(BaseModel):
    bids_root: str = Field(description="Path to BIDS dataset root directory")


class BIDSDatasetSummary(BaseModel):
    dataset_path: str
    num_subjects: int
    subjects: list[str]
    num_sessions: int
    modalities: list[str]
    total_scans: int
    task_names: list[str]
    has_derivatives: bool


# ---------- Tool 4: validate_bids ----------

class ValidateBIDSInput(BaseModel):
    bids_root: str = Field(description="Path to BIDS dataset root directory")


class ValidationReport(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    summary: str
