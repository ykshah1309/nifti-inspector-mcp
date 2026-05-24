# nifti-inspector-mcp

MCP server for inspecting NIfTI neuroimaging files and BIDS datasets. Built for AI agents that need to read, validate, and reason about brain imaging data with full provenance.

## Installation

```bash
git clone https://github.com/ykshah1309/nifti-inspector-mcp.git
cd nifti-inspector-mcp
pip install -e .
python tests/generate_sample_data.py
```

Requires Python 3.11+.

Optional: install the official BIDS validator CLI for full validation. Without it, `validate_bids` falls back to a basic structural check.

```bash
npm install -g bids-validator
```

## Configuration — Claude Desktop

Add this to your `claude_desktop_config.json`:

- macOS / Linux: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nifti-inspector": {
      "command": "nifti-inspector"
    }
  }
}
```

If the `nifti-inspector` console script isn't on your PATH (e.g. when using a venv), point at your interpreter instead:

```json
{
  "mcpServers": {
    "nifti-inspector": {
      "command": "python",
      "args": ["-m", "nifti_inspector.server"]
    }
  }
}
```

Restart Claude Desktop after editing. The four tools will appear in the tool picker.

## Tools

### `load_nifti`
Returns header metadata for a `.nii` / `.nii.gz` file.

Input: `{"path": "/data/sub-01_T1w.nii.gz"}`
Output: dimensions, voxel size (mm), datatype, number of volumes, 4x4 affine, units, intent code.

### `check_motion`
Estimates frame-to-frame motion in a 4D fMRI run via intensity-weighted center-of-mass displacement. Flags volumes exceeding a threshold (default 2.0 mm).

Input: `{"path": "/data/sub-01_task-rest_bold.nii.gz", "threshold_mm": 2.0}`
Output: total volumes, list of flagged volume indices, max/mean displacement, threshold used.

> Note: this is a lightweight proxy. For research-grade motion correction use FSL MCFLIRT, AFNI 3dvolreg, or fMRIPrep.

### `summarize_bids`
Summarizes a BIDS dataset using pybids.

Input: `{"bids_root": "/data/my-bids-study"}`
Output: subject count and list, session count, modalities present, task names, total scan count, derivatives flag.

### `validate_bids`
Validates a BIDS dataset. Uses the official `bids-validator` CLI if installed on PATH; otherwise runs a basic structural check (presence of `dataset_description.json`, subject directories, modality subdirectories).

Input: `{"bids_root": "/data/my-bids-study"}`
Output: is_valid, errors, warnings, summary.

## Example queries

In Claude Desktop, with the server registered:

- "Inspect this NIfTI file at /Users/yash/data/scan.nii.gz and tell me its dimensions and voxel size."
- "Check this fMRI for motion artifacts and report any flagged volumes: /Users/yash/data/sub-01_task-rest_bold.nii.gz"
- "Summarize the BIDS dataset at /Users/yash/data/my-study."
- "Validate that /Users/yash/data/my-study is BIDS-compliant and report any errors."

## Provenance

Every tool call is logged by the MCP protocol with typed inputs and outputs. This creates an audit trail suitable for reproducibility-critical research workflows — inputs, outputs, and the exact tool invoked are recorded by the client.

## Running the tests

```bash
pip install -e ".[dev]"
python tests/generate_sample_data.py
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).

## Author

Yash Kamlesh Shah — [github.com/ykshah1309](https://github.com/ykshah1309)
