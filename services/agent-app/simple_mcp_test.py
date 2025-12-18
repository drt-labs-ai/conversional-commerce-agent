import asyncio
import os
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

MCP_SERVER_URL = os.getenv("SAP_MCP_SERVER_URL", "http://sap-mcp-server:8001/sse")

async def test_connection():
    print(f"Connecting to {MCP_SERVER_URL}...")
    try:
        async with sse_client(MCP_SERVER_URL) as streams:
            print("SSE Connected. Initialize Session...")
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                print("Session Initialized. Listing Tools...")
                tools = await session.list_tools()
                print(f"Tools Found: {[t.name for t in tools.tools]}")
                
                print("Calling search_products...")
                result = await session.call_tool("search_products", arguments={"query": "camera"})
                print(f"Search Result: {result.content[0].text[:100]}...")
                
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
