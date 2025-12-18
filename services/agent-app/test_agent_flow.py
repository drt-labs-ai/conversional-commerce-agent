import asyncio
import os
from langchain_core.messages import HumanMessage
from agent_graph import create_agent_graph

# Mock configuration for the session
config = {"configurable": {"thread_id": "test_thread_1"}}

async def test_search_and_cart():
    print("--- Initializing Agent Graph ---")
    app = await create_agent_graph()
    
    print("\n--- Test 1: Product Search ---")
    # User asks to search
    input_1 = {"messages": [HumanMessage(content="Find me a digital camera")]}
    
    async for event in app.astream(input_1, config=config):
        # Print only the final message from each node to reduce noise
        for key, value in event.items():
            if "messages" in value:
                print(f"[{key}]: {value['messages'][-1].content}")
            else:
                 print(f"[{key}]: {value}")

    print("\n--- Test 2: Add to Cart ---")
    # User asks to add to cart (assumes context from previous turn is saved via checkpointer)
    input_2 = {"messages": [HumanMessage(content="Add the first camera you found to my cart")]}
    
    async for event in app.astream(input_2, config=config):
        for key, value in event.items():
            if "messages" in value:
                print(f"[{key}]: {value['messages'][-1].content}")
            else:
                 print(f"[{key}]: {value}")

if __name__ == "__main__":
    asyncio.run(test_search_and_cart())
