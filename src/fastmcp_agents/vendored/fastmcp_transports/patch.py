import subprocess
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, TextIO

import anyio
import anyio.lowlevel
import mcp.client.stdio
import mcp.types
from anyio.streams.text import TextReceiveStream
from fastmcp_agents.util.logging import BASE_LOGGER
from mcp import StdioServerParameters
from mcp.shared.message import SessionMessage

if TYPE_CHECKING:
    from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

logger = BASE_LOGGER.getChild(__name__)


@asynccontextmanager
async def stdio_client(server: StdioServerParameters, errlog: TextIO = sys.stderr):  # noqa: ARG001, PLR0915  # pyright: ignore[reportUnusedParameter]
    """
    Client transport for stdio: this will connect to a server by spawning a
    process and communicating with it over stdin/stdout.
    """

    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
    read_stream_writer: MemoryObjectSendStream[SessionMessage | Exception]

    write_stream: MemoryObjectSendStream[SessionMessage]
    write_stream_reader: MemoryObjectReceiveStream[SessionMessage]

    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    try:
        command = mcp.client.stdio._get_executable_command(server.command)  # pyright: ignore[reportPrivateUsage]

        # Open process with stderr piped for capture
        process = await mcp.client.stdio._create_platform_compatible_process(  # pyright: ignore[reportPrivateUsage]
            command=command,
            args=server.args,
            env=(
                {**mcp.client.stdio.get_default_environment(), **server.env}
                if server.env is not None
                else mcp.client.stdio.get_default_environment()
            ),
            errlog=subprocess.PIPE,  # pyright: ignore[reportArgumentType]
            cwd=server.cwd,
        )
    except OSError:
        # Clean up streams if process creation fails
        await read_stream.aclose()
        await write_stream.aclose()
        await read_stream_writer.aclose()
        await write_stream_reader.aclose()
        raise

    async def stderr_reader():
        assert process.stderr, "Opened process is missing stderr"  # noqa: S101
        try:
            async with read_stream:
                async for chunk in TextReceiveStream(
                    process.stderr,  # pyright: ignore[reportArgumentType]
                    encoding=server.encoding,
                    errors=server.encoding_error_handler,
                ):
                    logger.error("MCP Server stderr: " + chunk)
        except anyio.ClosedResourceError:
            await anyio.lowlevel.checkpoint()  # type: ignore

    async def stdout_reader():
        assert process.stdout, "Opened process is missing stdout"  # noqa: S101

        try:
            async with read_stream_writer:
                buffer = ""
                async for chunk in TextReceiveStream(
                    process.stdout,
                    encoding=server.encoding,
                    errors=server.encoding_error_handler,
                ):
                    lines = (buffer + chunk).split("\n")
                    buffer = lines.pop()

                    for line in lines:
                        try:
                            message = mcp.types.JSONRPCMessage.model_validate_json(line)
                        except Exception as exc:
                            await read_stream_writer.send(exc)
                            continue

                        session_message = SessionMessage(message)
                        await read_stream_writer.send(session_message)
        except anyio.ClosedResourceError:
            await anyio.lowlevel.checkpoint()  # type: ignore

    async def stdin_writer():
        assert process.stdin, "Opened process is missing stdin"  # noqa: S101

        try:
            async with write_stream_reader:
                async for session_message in write_stream_reader:
                    json = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                    await process.stdin.send(
                        (json + "\n").encode(
                            encoding=server.encoding,
                            errors=server.encoding_error_handler,
                        )
                    )
        except anyio.ClosedResourceError:
            await anyio.lowlevel.checkpoint()  # type: ignore

    async with (
        anyio.create_task_group() as tg,
        process,
    ):
        tg.start_soon(stdout_reader)
        tg.start_soon(stdin_writer)
        tg.start_soon(stderr_reader)
        try:
            yield read_stream, write_stream
        finally:
            # Clean up process to prevent any dangling orphaned processes
            try:
                if sys.platform == "win32":
                    await mcp.client.stdio.terminate_windows_process(process)  # pyright: ignore[reportPrivateImportUsage]
                else:
                    process.terminate()
            except ProcessLookupError:
                # Process already exited, which is fine
                pass
            await read_stream.aclose()
            await write_stream.aclose()
            await read_stream_writer.aclose()
            await write_stream_reader.aclose()


def apply_patches():
    mcp.client.stdio.stdio_client = stdio_client
