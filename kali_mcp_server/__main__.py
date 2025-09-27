"""Command line entry point for the Kali MCP server."""

from __future__ import annotations

import argparse
import asyncio
from typing import Iterable

from .server import create_server


async def _run(transport: str, *, host: str, port: int, mount_path: str) -> None:
    server = create_server(host=host, port=port)

    if transport == "stdio":
        await server.run_stdio_async()
    elif transport == "sse":
        await server.run_sse_async(mount_path=mount_path)
    elif transport == "http":
        await server.run_streamable_http_async()
    else:
        raise ValueError(f"Unsupported transport '{transport}'.")


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Kali MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "http"),
        default="stdio",
        help="Transport to expose (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host/interface for SSE or HTTP transports (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE or HTTP transports (default: 8000)",
    )
    parser.add_argument(
        "--mount-path",
        default="/",
        help="URL mount path when using the SSE transport (default: /)",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    asyncio.run(_run(args.transport, host=args.host, port=args.port, mount_path=args.mount_path))


if __name__ == "__main__":
    main()
