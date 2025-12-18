import os
import uvicorn
from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, EmbeddedResource, ImageContent
import mcp.types as types
from occ_client import SAPOCCClient

app = FastAPI()
mcp_server = Server("sap-commerce-mcp")
client = SAPOCCClient()

# Define Tools
TOOLS = [
    Tool(
        name="search_products",
        description="Search for products in the SAP Commerce catalog.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "page_size": {"type": "integer", "description": "Number of results per page", "default": 5}
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_product_details",
        description="Get detailed information about a specific product.",
        inputSchema={
            "type": "object",
            "properties": {
                "product_code": {"type": "string", "description": "The product code/ID"}
            },
            "required": ["product_code"]
        }
    ),
    Tool(
        name="create_cart",
        description="Create a new shopping cart.",
        inputSchema={
            "type": "object",
            "properties": {},
        }
    ),
    Tool(
        name="add_to_cart",
        description="Add a product to an existing cart.",
        inputSchema={
            "type": "object",
            "properties": {
                "cart_id": {"type": "string"},
                "product_code": {"type": "string"},
                "quantity": {"type": "integer", "default": 1}
            },
            "required": ["cart_id", "product_code"]
        }
    ),
    Tool(
        name="update_cart_entry",
        description="Update the quantity of an item in the cart.",
        inputSchema={
            "type": "object",
            "properties": {
                "cart_id": {"type": "string"},
                "entry_number": {"type": "integer"},
                "quantity": {"type": "integer"}
            },
            "required": ["cart_id", "entry_number", "quantity"]
        }
    ),
    Tool(
        name="get_cart",
        description="Get the current state of a cart.",
        inputSchema={
            "type": "object",
            "properties": {
                "cart_id": {"type": "string"}
            },
            "required": ["cart_id"]
        }
    ),
    Tool(
        name="set_delivery_address",
        description="Set the delivery address for the cart.",
        inputSchema={
            "type": "object",
            "properties": {
                "cart_id": {"type": "string"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "line1": {"type": "string"},
                "town": {"type": "string"},
                "postal_code": {"type": "string"},
                "country_isocode": {"type": "string"}
            },
            "required": ["cart_id", "first_name", "last_name", "line1", "town", "postal_code", "country_isocode"]
        }
    ),
    Tool(
        name="set_delivery_mode",
        description="Set the delivery mode for the cart.",
        inputSchema={
            "type": "object",
            "properties": {
                "cart_id": {"type": "string"},
                "mode": {"type": "string"}
            },
            "required": ["cart_id", "mode"]
        }
    ),
    Tool(
        name="place_order",
        description="Place an order from the cart.",
        inputSchema={
            "type": "object",
            "properties": {
                "cart_id": {"type": "string"}
            },
            "required": ["cart_id"]
        }
    )
]

@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.EmbeddedResource | types.ImageContent]:
    try:
        if name == "search_products":
            res_dict = await client.search_products(arguments["query"], pageSize=arguments.get("page_size", 5))
            # Simplify response to save tokens
            products = res_dict.get("products", [])
            simplified_products = []
            for p in products:
                simplified_products.append({
                    "name": p.get("name"),
                    "code": p.get("code"),
                    "price": p.get("price", {}).get("formattedValue"),
                    "description": p.get("summary", "")[:200], # Truncate description
                    "rating": p.get("averageRating")
                })
            return [TextContent(type="text", text=str(simplified_products))]
            
        elif name == "get_product_details":
            result = await client.get_product_details(arguments["product_code"])
            return [TextContent(type="text", text=str(result))]
            
        elif name == "create_cart":
            result = await client.create_cart()
            # Anonymous carts must use GUID, not Code.
            # We explicitly return the GUID as "Cart ID" to guide the LLM.
            guid = result.get("guid")
            if guid:
                return [TextContent(type="text", text=f"Cart Created. Cart ID: {guid}")]
            else:
                return [TextContent(type="text", text=str(result))]
            
        elif name == "add_to_cart":
            result = await client.add_to_cart(arguments["cart_id"], arguments["product_code"], arguments.get("quantity", 1))
            return [TextContent(type="text", text=str(result))]
            
        elif name == "update_cart_entry":
            result = await client.update_cart_entry(arguments["cart_id"], arguments["entry_number"], arguments["quantity"])
            return [TextContent(type="text", text=str(result))]
            
        elif name == "get_cart":
            result = await client.get_cart(arguments["cart_id"])
            return [TextContent(type="text", text=str(result))]
            
        elif name == "set_delivery_address":
            address = {
                "firstName": arguments["first_name"],
                "lastName": arguments["last_name"],
                "line1": arguments["line1"],
                "town": arguments["town"],
                "postalCode": arguments["postal_code"],
                "country": {"isocode": arguments["country_isocode"]}
            }
            result = await client.set_delivery_address(arguments["cart_id"], address)
            return [TextContent(type="text", text=str(result))]

        elif name == "set_delivery_mode":
            result = await client.set_delivery_mode(arguments["cart_id"], arguments["mode"])
            return [TextContent(type="text", text=str(result))]

        elif name == "place_order":
            result = await client.place_order(arguments["cart_id"])
            return [TextContent(type="text", text=str(result))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

# SSE Endpoint for MCP
sse = SseServerTransport("/sse")

async def handle_sse(scope, receive, send):
    """
    Handle SSE connection using raw ASGI to avoid FastAPI response conflicts.
    """
    async with sse.connect_sse(scope, receive, send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

async def handle_messages(scope, receive, send):
    """
    Handle POST messages using raw ASGI.
    """
    await sse.handle_post_message(scope, receive, send)

# Register endpoints (using Starlette's add_route/add_websocket_route logic but for raw ASGI)
# Since FastAPI/Starlette routes expect Request->Response, we can use a raw ASGI function if we register it carefully
# OR we can simply wrap it in a function that takes existing args if we use add_route but that expects a Request object.

# Best approach: Use a wrapper that extracts scope/receive/send from Request IF using add_route
# or strictly route via Mount if it was a full app. 
# But let's simple Replace the @app.get with a specialized handler that returns a Response that does nothing? No.

# Let's use the valid Starlette pattern for manual ASGI handling in a route:
# Endpoint can be an ASGI app function (request, receive, send) -> No, endpoint(request).
# BUT, we can just access request.scope, request.receive and use the send passed by the server?
# request object in FastAPI doesn't carry 'send' usually in the public API.

# Better approach that works: specific standard ASGI app mounting.
class MCP_SSE_ASGI:
    async def __call__(self, scope, receive, send):
        if scope["method"] == "GET":
             async with sse.connect_sse(scope, receive, send) as streams:
                await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())
        elif scope["method"] == "POST":
             await sse.handle_post_message(scope, receive, send)

app.mount("/sse", MCP_SSE_ASGI())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
