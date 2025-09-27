"""Factory for the Kali MCP server."""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import textwrap
import time
from typing import Iterable, Sequence

from mcp.server.fastmcp import Context, FastMCP

from .commands import CommandSpec, get_command, iter_commands
from .models import CommandExecutionResult, CommandInfo

_MAX_CAPTURE_BYTES = 65_536


def _truncate_output(raw: bytes, *, limit: int = _MAX_CAPTURE_BYTES) -> str:
    """Convert captured process output to a bounded UTF-8 string."""

    text = raw.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    omitted = len(text) - limit
    return f"{truncated}\n...[truncated {omitted} characters]"


def _spec_to_info(spec: CommandSpec) -> CommandInfo:
    return CommandInfo(
        name=spec.name,
        binary=spec.binary,
        description=spec.description,
        default_args=list(spec.default_args),
        allowed_flags=sorted(spec.allowed_flags),
        allowed_flag_prefixes=list(spec.allowed_flag_prefixes),
        installed=spec.is_installed(),
        example=spec.example,
        notes=spec.notes,
    )


async def _execute_command(
    spec: CommandSpec,
    arguments: Sequence[str],
    *,
    context: Context | None,
    dry_run: bool,
) -> CommandExecutionResult:
    """Execute a command according to its specification."""

    binary_path = shutil.which(spec.binary)
    if binary_path is None:
        if context is not None:
            await context.warning(
                f"Binary '{spec.binary}' was not found in PATH. Returning a synthetic result."
            )
            await context.report_progress(100, 100)
        return CommandExecutionResult(
            command=spec.name,
            binary=spec.binary,
            arguments=list(arguments),
            status="missing",
            returncode=None,
            stdout="",
            stderr="",
            duration_ms=0.0,
            message="Executable not installed on this system.",
        )

    if dry_run:
        if context is not None:
            await context.info(
                "Dry run requested; returning the normalised command without executing it."
            )
            await context.report_progress(100, 100)
        return CommandExecutionResult(
            command=spec.name,
            binary=binary_path,
            arguments=list(arguments),
            status="success",
            returncode=None,
            stdout="",
            stderr="",
            duration_ms=0.0,
            message="Dry run only; no process was started.",
        )

    start = time.perf_counter()
    if context is not None:
        await context.report_progress(5, 100)
        await context.info(
            f"Launching {spec.binary} with arguments: {' '.join(arguments) or '<none>'}"
        )

    process = await asyncio.create_subprocess_exec(
        binary_path,
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=spec.timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(process.communicate(), timeout=5)
        duration = (time.perf_counter() - start) * 1000
        if context is not None:
            await context.error(
                f"{spec.name} exceeded the configured timeout of {spec.timeout:.0f} seconds."
            )
            await context.report_progress(100, 100)
        return CommandExecutionResult(
            command=spec.name,
            binary=binary_path,
            arguments=list(arguments),
            status="timeout",
            returncode=None,
            stdout="",
            stderr="",
            duration_ms=duration,
            message=f"Command timed out after {spec.timeout:.0f} seconds.",
        )

    duration = (time.perf_counter() - start) * 1000
    stdout = _truncate_output(stdout_bytes)
    stderr = _truncate_output(stderr_bytes)
    status = "success" if process.returncode == 0 else "error"
    message = None if status == "success" else f"Process exited with code {process.returncode}."

    if context is not None:
        await context.report_progress(100, 100)
        if status == "success":
            await context.info(f"{spec.name} completed successfully in {duration:.0f} ms.")
        else:
            await context.error(message or "Command reported an error.")

    return CommandExecutionResult(
        command=spec.name,
        binary=binary_path,
        arguments=list(arguments),
        status=status,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration,
        message=message,
    )


def _render_reference(specs: Iterable[CommandSpec]) -> str:
    """Render a Markdown reference document describing all commands."""

    lines: list[str] = ["# Kali MCP Command Reference", ""]
    for spec in sorted(specs, key=lambda item: item.name):
        lines.append(f"## {spec.name}")
        lines.append("")
        lines.append(spec.description)
        lines.append("")
        lines.append(f"* Binary: `{spec.binary}`")
        if spec.default_args:
            lines.append(f"* Default arguments: {' '.join(spec.default_args)}")
        if spec.allowed_flags:
            flags = "`, `".join(sorted(spec.allowed_flags))
            lines.append(f"* Allowed flags: `{flags}`")
        if spec.allowed_flag_prefixes:
            prefixes = "`, `".join(spec.allowed_flag_prefixes)
            lines.append(f"* Allowed flag prefixes: `{prefixes}`")
        lines.append(f"* Timeout: {spec.timeout:.0f} seconds")
        if spec.example:
            lines.append(f"* Example: `{spec.example}`")
        if spec.notes:
            lines.append(f"* Notes: {spec.notes}")
        lines.append("")
    return "\n".join(lines)


_INSTRUCTIONS = textwrap.dedent(
    """
    This server exposes safe wrappers around popular Kali Linux tooling.

    * Use `list_commands` to enumerate the allow-listed utilities and check which
      binaries are available on the current host.
    * `describe_command` returns detailed metadata about a specific tool, including
      allowed flags and timeouts.
    * `run_command` executes a tool with validated arguments. Only documented flags
      and prefix forms are accepted, and positional arguments are sanitised to avoid
      shell injection. Many heavy-weight tools may not be installed in the runtime
      environment; always inspect `installed` before execution.
    * Set the optional `dry_run` parameter when you only need the normalised
      invocation without actually launching the command.
    """
).strip()


def create_server(*, host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    """Create and configure the Kali MCP server instance."""

    server = FastMCP(
        name="kali-mcp-server",
        instructions=_INSTRUCTIONS,
        host=host,
        port=port,
    )

    @server.resource(
        "resource://kali/commands",
        name="kali-commands",
        title="Kali MCP command reference",
        description="Markdown reference describing the allow-listed Kali commands.",
        mime_type="text/markdown",
    )
    def command_reference() -> str:
        return _render_reference(iter_commands())

    @server.tool(
        name="list_commands",
        description="Return metadata for all allow-listed commands.",
        structured_output=True,
    )
    def list_commands(only_installed: bool = False) -> list[CommandInfo]:
        specs = list(iter_commands())
        if only_installed:
            specs = [spec for spec in specs if spec.is_installed()]
        return [_spec_to_info(spec) for spec in sorted(specs, key=lambda item: item.name)]

    @server.tool(
        name="describe_command",
        description="Return metadata for a single allow-listed command.",
        structured_output=True,
    )
    def describe_command(command: str) -> CommandInfo:
        try:
            spec = get_command(command)
        except KeyError as exc:
            raise ValueError(str(exc)) from exc
        return _spec_to_info(spec)

    @server.tool(
        name="run_command",
        description="Execute an allow-listed Kali command with validated arguments.",
        structured_output=True,
    )
    async def run_command(
        command: str,
        arguments: Sequence[str] | None = None,
        dry_run: bool = False,
        context: Context | None = None,
    ) -> CommandExecutionResult:
        try:
            spec = get_command(command)
        except KeyError as exc:
            raise ValueError(str(exc)) from exc

        try:
            normalised_args = spec.normalize_arguments(arguments or [])
        except ValueError as exc:
            if context is not None:
                await context.error(str(exc))
            raise

        return await _execute_command(spec, normalised_args, context=context, dry_run=dry_run)

    return server


__all__ = ["create_server"]
