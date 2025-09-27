"""Pydantic models used by the Kali MCP server."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CommandInfo(BaseModel):
    """Metadata describing an allowed command."""

    name: str = Field(..., description="Human friendly command identifier")
    binary: str = Field(..., description="Executable name invoked on the system")
    description: str = Field(..., description="Short explanation of the command purpose")
    default_args: list[str] = Field(default_factory=list, description="Arguments applied automatically")
    allowed_flags: list[str] = Field(default_factory=list, description="Safe flags that may be provided verbatim")
    allowed_flag_prefixes: list[str] = Field(
        default_factory=list,
        description="Flag prefixes that enable parameterised arguments (e.g. -p80)",
    )
    installed: bool = Field(..., description="Whether the executable was found in $PATH at runtime")
    example: Optional[str] = Field(None, description="Example invocation for quick reference")
    notes: Optional[str] = Field(None, description="Additional hints or caveats for the command")


class CommandExecutionResult(BaseModel):
    """Normalised output from executing an allow-listed command."""

    command: str = Field(..., description="Logical command identifier")
    binary: str = Field(..., description="Concrete binary executed")
    arguments: list[str] = Field(default_factory=list, description="Arguments passed to the binary")
    status: Literal["success", "error", "missing", "timeout"] = Field(
        ..., description="Final outcome of the execution request"
    )
    returncode: Optional[int] = Field(None, description="Process return code when available")
    stdout: str = Field("", description="Captured standard output (truncated if necessary)")
    stderr: str = Field("", description="Captured standard error (truncated if necessary)")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    message: Optional[str] = Field(None, description="Human readable message describing the outcome")


__all__ = ["CommandInfo", "CommandExecutionResult"]
