import os
import asyncio
from typing import List, Any, Callable
from langchain_core.tools import Tool
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# Configuration
MCP_SERVER_URL = os.getenv("SAP_MCP_SERVER_URL", "http://sap-mcp-server:8001/sse")

async def get_mcp_tools() -> List[Tool]:
    """
    Connects to the MCP server, fetches available tools, and returns them as LangChain Tools.
    Note: For a long-running app this needs to manage the session persistence.
    For simplicity here, we might create a wrapper that establishes a session per call 
    or maintains a global session if possible.
    """
    # This is a complex part because MCP is stateful.
    # We will create a proxy tool that opens a connection, calls the tool, and closes it (inefficient)
    # OR we need a persistent manager. 
    # Let's try to list tools first to define them, then execution logic.
    
    # We'll define the known tools manually to map them to the MCP calls for stability,
    # relying on the server to handle the execution.
    
    tools = []
    
    # Helper to execute a tool on the MCP server
    async def execute_mcp_tool(tool_name: str, **kwargs):
        async with sse_client(MCP_SERVER_URL) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=kwargs)
                return result.content[0].text # Access text content

    # Define tools 
    # Product Search
    async def search_products_wrapper(query: str, page_size: int = 5):
        return await execute_mcp_tool("search_products", query=query, page_size=page_size)
    
    tools.append(Tool(
        name="search_products",
        func=None,
        coroutine=search_products_wrapper,
        description="Search for products in the SAP catalog. Args: query, page_size"
    ))

    # Product Details
    async def get_product_details_wrapper(product_code: str):
        return await execute_mcp_tool("get_product_details", product_code=product_code)
    
    tools.append(Tool(
        name="get_product_details",
        func=None,
        coroutine=get_product_details_wrapper,
        description="Get product details. Args: product_code"
    ))

    # Create Cart
    async def create_cart_wrapper():
        return await execute_mcp_tool("create_cart")
        
    tools.append(Tool(
        name="create_cart",
        func=None,
        coroutine=create_cart_wrapper,
        description="Create a new cart. Returns cart ID."
    ))

    # Add to Cart
    async def add_to_cart_wrapper(cart_id: str, product_code: str, quantity: int = 1):
        return await execute_mcp_tool("add_to_cart", cart_id=cart_id, product_code=product_code, quantity=quantity)

    tools.append(Tool(
        name="add_to_cart",
        func=None,
        coroutine=add_to_cart_wrapper,
        description="Add product to cart. Args: cart_id, product_code, quantity"
    ))

    # Get Cart
    async def get_cart_wrapper(cart_id: str):
        return await execute_mcp_tool("get_cart", cart_id=cart_id)

    tools.append(Tool(
        name="get_cart",
        func=None,
        coroutine=get_cart_wrapper,
        description="Get cart details. Args: cart_id"
    ))
    
    # Place Order
    async def place_order_wrapper(cart_id: str):
        return await execute_mcp_tool("place_order", cart_id=cart_id)

    tools.append(Tool(
        name="place_order",
        func=None,
        coroutine=place_order_wrapper,
        description="Place order. Args: cart_id"
    ))

    return tools
