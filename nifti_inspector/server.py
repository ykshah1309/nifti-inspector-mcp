"""MCP server entry point for nifti-inspector-mcp.

Exposes four tools over stdio using the low-level mcp.server.Server API.
Each tool delegates to a typed function in tools.py.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import BaseModel, ValidationError

from . import __version__
from .models import (
    CheckMotionInput,
    LoadNIfTIInput,
    SummarizeBIDSInput,
    ValidateBIDSInput,
)
from .tools import check_motion, load_nifti, summarize_bids, validate_bids

server: Server = Server("nifti-inspector-mcp")


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return a JSON schema for a Pydantic model with $defs inlined as best-effort."""
    return model.model_json_schema()


@server.list_tools()
async def _list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="load_nifti",
            description=(
                "Load a NIfTI file (.nii / .nii.gz) and return its header metadata: "
                "dimensions, voxel size, datatype, number of volumes, affine matrix, "
                "spatial/temporal units, and intent code."
            ),
            inputSchema=_schema(LoadNIfTIInput),
        ),
        types.Tool(
            name="check_motion",
            description=(
                "Estimate frame-to-frame motion in a 4D fMRI NIfTI file by computing "
                "intensity-weighted center-of-mass shifts between consecutive volumes. "
                "Flags volumes exceeding a displacement threshold (default 2.0 mm). "
                "Note: this is a lightweight proxy, not a substitute for FSL MCFLIRT."
            ),
            inputSchema=_schema(CheckMotionInput),
        ),
        types.Tool(
            name="summarize_bids",
            description=(
                "Summarize a BIDS dataset using pybids: subject count, session count, "
                "modalities present (anat/func/dwi/...), task names, total scan count, "
                "and whether a derivatives/ directory exists."
            ),
            inputSchema=_schema(SummarizeBIDSInput),
        ),
        types.Tool(
            name="validate_bids",
            description=(
                "Validate a BIDS dataset. Uses the official bids-validator CLI if "
                "installed on PATH; otherwise performs a basic structural check "
                "(dataset_description.json present, sub-XX/ directories exist with "
                "modality subdirectories)."
            ),
            inputSchema=_schema(ValidateBIDSInput),
        ),
    ]


def _ok(model: BaseModel) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=model.model_dump_json(indent=2))]


def _err(msg: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps({"error": msg}, indent=2))]


@server.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        if name == "load_nifti":
            return _ok(load_nifti(LoadNIfTIInput(**arguments)))
        if name == "check_motion":
            return _ok(check_motion(CheckMotionInput(**arguments)))
        if name == "summarize_bids":
            return _ok(summarize_bids(SummarizeBIDSInput(**arguments)))
        if name == "validate_bids":
            return _ok(validate_bids(ValidateBIDSInput(**arguments)))
        return _err(f"Unknown tool: {name}")
    except ValidationError as exc:
        return _err(f"Input validation failed: {exc}")
    except FileNotFoundError as exc:
        return _err(str(exc))
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:  # noqa: BLE001 — surface any tool error to the client
        return _err(f"{type(exc).__name__}: {exc}")


async def _run() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nifti-inspector-mcp",
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
