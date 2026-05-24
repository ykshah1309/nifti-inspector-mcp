# Live Demo Script — nifti-inspector-mcp

**When:** Wednesday May 27, 2026, 2:30 PM ET
**Where:** Fenster Hall 606, NJIT
**Audience:** BME researchers (fMRI / DTI / structural MRI)
**Duration:** ~7-10 minutes of live demo + Q&A

---

## 0. Pre-demo checklist (do this 30 min before)

```bash
cd C:\Users\yksha\bme-mcp
python -m pip install -e ".[dev]"             # only if not already installed
python tests/generate_sample_data.py           # regenerate sample NIfTI/BIDS
python -m pytest tests/                        # all 6 tests should pass
where nifti-inspector                          # confirm console script is on PATH
```

Then **fully quit and restart Claude Desktop** so it re-reads the config and re-spawns the MCP server. Verify the tools appear in the tools picker (4 tools: `load_nifti`, `check_motion`, `summarize_bids`, `validate_bids`).

If anything fails here, switch to the fallback plan (see bottom).

### Claude Desktop config used during the demo

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nifti-inspector": {
      "command": "nifti-inspector"
    }
  }
}
```

### Paths to copy into the chat (Windows)

- T1w:  `C:\Users\yksha\bme-mcp\tests\sample_data\sub-01_T1w.nii.gz`
- BOLD: `C:\Users\yksha\bme-mcp\tests\sample_data\sub-01_task-rest_bold.nii.gz`
- BIDS: `C:\Users\yksha\bme-mcp\tests\sample_data\bids_demo`

Keep these in a sticky note or open a Notepad with them ready to paste.

---

## 1. Opening (30 sec)

> "MCP — the Model Context Protocol — is how Anthropic lets language models call typed tools. I built a small MCP server that exposes four neuroimaging-specific tools. The point is that Claude can now read and reason about your NIfTI files and BIDS datasets directly, with every call logged and typed. Watch."

---

## 2. Tool 1 — `load_nifti` (1 min)

**Prompt:**

> I have a NIfTI file at `C:\Users\yksha\bme-mcp\tests\sample_data\sub-01_T1w.nii.gz`. Can you inspect it and tell me about it?

**Expected:** Claude calls `load_nifti` and returns dimensions `[32, 32, 16]`, voxel size `[1.0, 1.0, 1.0]` mm, datatype `float32`, 1 volume, 4x4 identity affine.

**Talking point:** "Notice this is structured output — Pydantic-typed. Claude didn't hallucinate the shape; the tool returned it."

---

## 3. Tool 2 — `check_motion` (1.5 min)

**Prompt:**

> Now check this fMRI run for motion artifacts: `C:\Users\yksha\bme-mcp\tests\sample_data\sub-01_task-rest_bold.nii.gz`

**Expected:** Claude calls `check_motion` with the default 2.0 mm threshold and reports flagged volumes **including 8 and 15** — those are the volumes I intentionally displaced in the synthetic data so the demo has something to show.

**Talking point:** "This is a center-of-mass proxy — for production work you'd pipe to FSL MCFLIRT. The point is the tool is composable: Claude can chain `summarize_bids` -> `check_motion` on every BOLD run in a study without me writing a script."

---

## 4. Tool 3 — `summarize_bids` (1.5 min)

**Prompt:**

> Summarize the BIDS dataset at `C:\Users\yksha\bme-mcp\tests\sample_data\bids_demo`.

**Expected:** Claude calls `summarize_bids` and reports 2 subjects (sub-01, sub-02), modalities anat + func, task `rest`, 3 scans.

**Optional follow-up:** "Which subject is missing the BOLD run?" — Claude will infer from the summary that sub-02 has only T1w.

---

## 5. Tool 4 — `validate_bids` (1 min)

**Prompt:**

> And validate that it's BIDS-compliant.

**Expected:** Claude calls `validate_bids` -> `is_valid: true`, no errors, summary line that says either "bids-validator CLI" (if installed) or "Basic Python BIDS structure check" (fallback).

**Talking point:** "If the official `bids-validator` npm tool is on PATH, the server shells out to it; otherwise it falls back to a structural sanity check. Install path stays tiny."

---

## 6. Closing (1 min)

> "Every one of those calls — inputs, outputs, the exact tool name — was logged by the MCP protocol. That's the provenance story: an audit trail that's reproducible across machines and over time. The whole server is ~300 lines of Python. The repo is on GitHub at github.com/ykshah1309/nifti-inspector-mcp — clone it, point Claude Desktop at it, you're inspecting your own data in five minutes."

---

## Fallback plan (if live demo fails)

1. **Don't panic, don't apologize.** Say: "Let me show you what this looks like in pre-recorded form."
2. Open `demo_screenshots/` (capture these the night before — one screenshot per tool call showing prompt + response).
3. Walk through the same four prompts using the screenshots.
4. After the talk, offer: "Happy to do it live with anyone in their office afterward."

### Common failure modes and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Tools don't appear in Claude Desktop | Config not picked up | Fully quit Claude (system tray → Quit), reopen |
| Server crashes on first call | Path has spaces / wrong slashes | Quote the path; use forward slashes or escaped backslashes |
| `nifti-inspector` not found | Console script not on PATH | Switch config to `python -m nifti_inspector.server` form (see README) |
| `validate_bids` says "BIDS root not found" | Pasted a file path not a directory | Use the `bids_demo` folder path |

### Screenshot capture commands (run the night before)

In Claude Desktop, run each prompt above and `Win+Shift+S` -> save to `demo_screenshots/01-load_nifti.png`, `02-check_motion.png`, `03-summarize_bids.png`, `04-validate_bids.png`.
