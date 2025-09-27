# Kali MCP Server

This repository provides a ready-to-run [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) server that exposes a curated, safe subset of popular Kali Linux tooling. It is designed to let AI agents run common discovery and reconnaissance utilities without granting unrestricted shell access.

## Features

- Allow-listed wrappers around widely used Kali utilities such as `nmap`, `sqlmap`, `gobuster`, `curl`, `ssh`, and more.
- Strict argument validation with per-command timeouts to reduce the risk of destructive execution or accidental long-running scans.
- Rich metadata describing each command, including default arguments, accepted flags, and example invocations.
- A Markdown reference resource (`resource://kali/commands`) that can be rendered directly by MCP-aware clients.
- Multiple transport options (stdio, SSE, or streamable HTTP) exposed through a simple command line interface.

## Getting Started

1. Install the project dependencies (Python 3.11+ is recommended):

   ```bash
   pip install -e .
   ```

2. Launch the server using the desired transport. For example, to run over stdio (ideal when embedding inside an MCP-compatible agent):

   ```bash
   python -m kali_mcp_server
   ```

   Or to expose the SSE transport on port 8000:

   ```bash
   python -m kali_mcp_server --transport sse --host 0.0.0.0 --port 8000
   ```

## MCP Tools

The server registers three primary MCP tools:

- `list_commands` — returns metadata for every allow-listed command. Pass `only_installed=true` to filter the list to binaries present on the host.
- `describe_command` — inspects a single command by name and returns its documentation, allowed flags, timeouts, and installation status.
- `run_command` — executes a command with validated arguments. Use the optional `dry_run=true` flag to preview the normalised invocation without launching the process.

A rendered Markdown overview is also available via the `resource://kali/commands` resource.

> **Note:** The execution environment used by this repository may not include the full Kali toolchain. Always consult the `installed` attribute returned by `list_commands`/`describe_command` before attempting to run a command.

## Development

Run a quick sanity check to ensure the code compiles:

```bash
python -m compileall kali_mcp_server
```

Contributions are welcome via pull requests.
