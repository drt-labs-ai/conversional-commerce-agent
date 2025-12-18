import asyncio
import os
import sys
from langchain_core.messages import HumanMessage, AIMessage

# Add /app to sys.path
sys.path.append("/app")

try:
    from agent_logic import create_agent_graph
except ImportError:
    print("WARNING: Could not import agent_logic.")

async def run_turn(graph, inputs, config):
    print(f"\nUser: {inputs['messages'][0].content}")
    async for event in graph.astream(inputs, config=config):
        # We can print events if we want detailed debugging
        pass
        
    # Get final state
    state = await graph.aget_state(config)
    messages = state.values.get("messages", [])
    if messages:
        last_msg = messages[-1]
        print(f"Agent: {last_msg.content}")
        return last_msg.content, messages
    return "", messages

async def test_search_flow(graph, config):
    print("\n=== Test Flow 1: Product Search ===")
    inputs = {"messages": [HumanMessage(content="Show me some cameras")]}
    content, _ = await run_turn(graph, inputs, config)
    
    if "camera" in content.lower() or "digital" in content.lower():
        print("SUCCESS: Search Flow")
        return True
    else:
        print("FAIL: Search Flow results irrelevant")
        return False

async def test_cart_flow(graph):
    print("\n=== Test Flow 2: Add to Cart ===")
    # Assuming previous context is preserved in 'config' thread_id
    
    # 1. Ask to add to cart
    # We rely on the agent remembering the products from the previous turn or searching again if needed.
    # To be safe, let's be explicit "Add the first camera results to my cart" or "Add product 12345 to cart"
    # But real user flow is "Add the first one". Let's try that.
    
    inputs = {"messages": [HumanMessage(content="Add the first product to my cart")]}
    content, messages = await run_turn(graph, inputs, config)
    
    # Check if a tool was called. The last message is AI response. 
    # Validating if 'add_to_cart' was actually executed is best done by checking tool messages in history 
    # or the text saying "Added".
    
    tool_calls_found = False
    for msg in messages:
        # Check recent messages for ToolMessage or AIMessage with tool_calls
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] in ["create_cart", "add_to_cart"]:
                    tool_calls_found = True
                    print(f"DEBUG: Found tool call {tc['name']}")
    
    if "added" in content.lower() or "cart" in content.lower() or tool_calls_found:
        print("SUCCESS: Cart Flow (Appears successful)")
        return True
    else:
        print("FAIL: Cart Flow (No confirmation or tool call detected)")
        return False

async def test_cart_flow(graph):
    print("\n=== Test Flow 2: Add to Cart (Fresh Session) ===")
    config = {"recursion_limit": 50, "configurable": {"thread_id": "test_cart_user"}}
    
    
    product_code = "CONF_CAMERA_SL"
    
    inputs = {"messages": [HumanMessage(content=f"Add product {product_code} to my cart")]}
    
    
    # inputs = {"messages": [HumanMessage(content="Add the first camera to my cart")]}
    content, messages = await run_turn(graph, inputs, config)
    
    # ... check for create_cart/add_to_cart ...
    cart_id = None
    tool_calls_found = False
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] in ["create_cart", "add_to_cart"]:
                    tool_calls_found = True
                    # Try to extract cart ID if available in content (not robust but okay for verification)
    
    # Extract Cart ID from Agent response if possible, or we need to debug print it
    # For automated test of Update, we will do a fresh setup in Python to avoid context bloat.
    
    if "added" in content.lower() or "cart" in content.lower() or tool_calls_found:
        print("SUCCESS: Cart Flow (Add)")
    else:
        print("FAIL: Cart Flow (Add)")

async def test_update_flow(graph):
    """
    Separate test for Update Quantity that sets up its own state to avoid LLM Context overflow.
    This function manually calls the tools to set up a cart, then asks the Agent to update it.
    """
    print("\n=== Test Flow 3: Update Quantity (Isolated) ===")
    config = {"recursion_limit": 50, "configurable": {"thread_id": "test_update_user"}}
    
    # 1. Setup: Create Cart & Add Item directly via OCC Code (Simulation)
    # We can't easy invoke internal tools without the agent. 
    # Instead, we will tell the agent to do it in a fresh thread, but we will ONLY ask it to update.
    # BUT the agent needs to know the Cart ID.
    
    # Simplified approach: We rely on the Agent maintaining state in memory? 
    # No, MemorySaver is per thread.
    
    # Let's try a "One-Shot" Update command where we give the context explicitly.
    # "I have a cart with ID <guid> and item 0. Update quantity to 2."
    # To do this effectively, we need a valid CART ID.
    
    # HACK: We will use the debug script logic to CREATE a cart and get ID, then feed it to the agent.
    import httpx 
    import os
    base_url = "https://host.docker.internal:9002/occ/v2" # Inside Docker - HTTPS
    verify = False
    
    try:
        async with httpx.AsyncClient(verify=verify) as client:
            # Create Cart
            r = await client.post(f"{base_url}/electronics/users/anonymous/carts")
            cart_data = r.json()
            cart_id = cart_data.get("guid")
            
            # Add Item
            await client.post(f"{base_url}/electronics/users/anonymous/carts/{cart_id}/entries", json={"product":{"code": "CONF_CAMERA_SL"}, "quantity": 1})
            
            print(f"DEBUG: Setup Cart {cart_id} with 1 item.")
    except Exception as e:
        print(f"SKIP: Could not setup SAP Cart directly ({e}). Skipping Update Test.")
        return

    # 2. Agent Turn
    # We provide the Cart ID in the prompt so the agent knows what to operate on without history.
    prompt = f"I have a cart with ID {cart_id}. Update the quantity of entry 0 to 2."
    inputs = {"messages": [HumanMessage(content=prompt)]}
    
    content, messages = await run_turn(graph, inputs, config)
    
    # Verify
    update_found = False
    for msg in messages:
         if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "update_cart_entry":
                    update_found = True
                    args = tc["args"]
                    if args.get("quantity") == 2:
                        print("SUCCESS: Update Quantity Tool Called correctly.")
                        return

    if "updated" in content.lower() or update_found:
        print("SUCCESS: Update Quantity Flow (Response)")
    else:
        print("FAIL: Update Quantity Flow")


async def main():
    print("Initializing Agent Graph...")
    graph = await create_agent_graph()
    
    # Test 2: Cart Add
    await test_cart_flow(graph)
    
    # Test 3: Update Quantity (Isolated)
    await test_update_flow(graph)

if __name__ == "__main__":
    asyncio.run(main())
