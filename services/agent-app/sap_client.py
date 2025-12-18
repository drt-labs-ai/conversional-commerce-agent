import os
import asyncio
from typing import List, Any, Callable
from langchain_core.tools import StructuredTool
from mcp.client.session import ClientSession

# ... (Configuration stays the same)

async def get_mcp_tools() -> List[StructuredTool]:
    # ... (execute_mcp_tool helper stays the same) ...
    
    # Helper to execute a tool on the MCP server using SSE transport
    async def execute_mcp_tool(tool_name: str, **kwargs):
        from mcp.client.sse import sse_client
        
        url = os.getenv("SAP_MCP_SERVER_URL", "http://sap-mcp-server:8001/sse")

        try:
            async with sse_client(url=url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=kwargs)
                    if result.isError:
                        return f"Tool execution error: {result}"
                    return result.content[0].text
        except Exception as e:
            return f"Error executing tool {tool_name}: {str(e)}"

    # Define tools 
    tools = []

    # Product Search
    async def search_products(query: str, page_size: int = 3):
        """Search for products in the SAP catalog."""
        return await execute_mcp_tool("search_products", query=query, page_size=page_size)
    
    tools.append(StructuredTool.from_function(
        coroutine=search_products,
        name="search_products",
        description="Search for products in the SAP catalog."
    ))

    # Product Details
    async def get_product_details(product_code: str):
        """Get detailed information about a specific product."""
        return await execute_mcp_tool("get_product_details", product_code=product_code)
    
    tools.append(StructuredTool.from_function(
        coroutine=get_product_details,
        name="get_product_details",
        description="Get detailed information about a specific product."
    ))

    # Create Cart
    async def create_cart():
        """Create a new shopping cart."""
        return await execute_mcp_tool("create_cart")
        
    tools.append(StructuredTool.from_function(
        coroutine=create_cart,
        name="create_cart",
        description="Create a new shopping cart. Returns cart ID."
    ))

    # Add to Cart
    async def add_to_cart(cart_id: str, product_code: str, quantity: int = 1):
        """Add a product to an existing cart."""
        return await execute_mcp_tool("add_to_cart", cart_id=cart_id, product_code=product_code, quantity=quantity)

    tools.append(StructuredTool.from_function(
        coroutine=add_to_cart,
        name="add_to_cart",
        description="Add product to cart."
    ))

    # Update Cart Entry
    async def update_cart_entry(cart_id: str, entry_number: int, quantity: int):
        """Update the quantity of a cart entry."""
        return await execute_mcp_tool("update_cart_entry", cart_id=cart_id, entry_number=entry_number, quantity=quantity)

    tools.append(StructuredTool.from_function(
        coroutine=update_cart_entry,
        name="update_cart_entry",
        description="Update cart item quantity."
    ))

    # Get Cart
    async def get_cart(cart_id: str):
        """Get the current state of a cart."""
        return await execute_mcp_tool("get_cart", cart_id=cart_id)

    tools.append(StructuredTool.from_function(
        coroutine=get_cart,
        name="get_cart",
        description="Get cart details."
    ))
    
    # Place Order
    async def place_order(cart_id: str):
        """Place an order from the cart."""
        return await execute_mcp_tool("place_order", cart_id=cart_id)

    tools.append(StructuredTool.from_function(
        coroutine=place_order,
        name="place_order",
        description="Place order."
    ))

    return tools
