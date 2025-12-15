import os
import uvicorn
from fastapi import FastAPI, Request
from mcp.server.fastapi import FasteAPIResource
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, EmbeddedResource, ImageContent
from occ_client import SAPOCCClient

app = FastAPI()
mcp_server = Server("sap-commerce-mcp")
client = SAPOCCClient()

@mcp_server.tool()
async def search_products(query: str, page_size: int = 5) -> str:
    """Search for products in the SAP Commerce catalog."""
    result = await client.search_products(query, pageSize=page_size)
    return str(result)

@mcp_server.tool()
async def get_product_details(product_code: str) -> str:
    """Get detailed information about a specific product."""
    result = await client.get_product_details(product_code)
    return str(result)

@mcp_server.tool()
async def create_cart() -> str:
    """Create a new shopping cart."""
    result = await client.create_cart()
    # Return just the cart ID or the full object? Full object is safer.
    return str(result)

@mcp_server.tool()
async def add_to_cart(cart_id: str, product_code: str, quantity: int = 1) -> str:
    """Add a product to an existing cart."""
    result = await client.add_to_cart(cart_id, product_code, quantity)
    return str(result)

@mcp_server.tool()
async def get_cart(cart_id: str) -> str:
    """Get the current state of a cart."""
    result = await client.get_cart(cart_id)
    return str(result)

@mcp_server.tool()
async def set_delivery_address(cart_id: str, first_name: str, last_name: str, line1: str, town: str, postal_code: str, country_isocode: str) -> str:
    """Set the delivery address for the cart."""
    address = {
        "firstName": first_name,
        "lastName": last_name,
        "line1": line1,
        "town": town,
        "postalCode": postal_code,
        "country": {"isocode": country_isocode}
    }
    result = await client.set_delivery_address(cart_id, address)
    return str(result)

@mcp_server.tool()
async def set_delivery_mode(cart_id: str, mode: str) -> str:
    """Set the delivery mode for the cart (e.g., 'standard-gross', 'premium-gross')."""
    result = await client.set_delivery_mode(cart_id, mode)
    return str(result)

@mcp_server.tool()
async def place_order(cart_id: str) -> str:
    """Place an order from the cart."""
    result = await client.place_order(cart_id)
    return str(result)

# SSE Endpoint for MCP
sse = SseServerTransport("/sse")

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
