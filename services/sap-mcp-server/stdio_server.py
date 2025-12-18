import asyncio
from mcp.server.stdio import stdio_server
from server import mcp_server

async def main():
    async with stdio_server() as (read, write):
        await mcp_server.run(
            read,
            write,
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
