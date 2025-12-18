import asyncio
import os
import sys
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

# Add /app to path to allow importing service modules
sys.path.append("/app")

try:
    from sap_client import get_mcp_tools
except ImportError:
    # Fallback if running locally vs in container might differ, but we expect to run in container
    print("WARNING: Could not import sap_client. MCP tests will fail.")

async def test_llm_connection():
    print("\n--- Test 1: LLM Simple Message ---")
    llm = ChatOpenAI(
        base_url=os.getenv("LLM_BASE_URL", "http://host.docker.internal:1234/v1"),
        api_key="lm-studio",
        model=os.getenv("MODEL_NAME", "mistral-7b-instruct-v0.3"),
        temperature=0
    )
    try:
        res = await llm.ainvoke([HumanMessage(content="Hello, answer with 'Pong'")])
        print(f"Response: {res.content}")
        if "Pong" in res.content:
            print("SUCCESS: LLM Connected")
        else:
            print("WARNING: LLM Connected but unexpected response")
    except Exception as e:
        print(f"FAIL: LLM Connection Error: {e}")

async def test_llm_tools():
    print("\n--- Test 2: LLM Tool Binding ---")
    llm = ChatOpenAI(
        base_url=os.getenv("LLM_BASE_URL", "http://host.docker.internal:1234/v1"),
        api_key="lm-studio",
        model=os.getenv("MODEL_NAME", "mistral-7b-instruct-v0.3"),
        temperature=0
    )
    
    @tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    try:
        llm_with_tools = llm.bind_tools([add])
        res = await llm_with_tools.ainvoke([HumanMessage(content="What is 2 + 2?")])
        print(f"Response Content: {res.content}")
        print(f"Tool Calls: {res.tool_calls}")
        
        if res.tool_calls and res.tool_calls[0]["name"] == "add":
            print("SUCCESS: LLM Tool Call Generated")
        else:
            print("FAIL: No tool call generated")
    except Exception as e:
        print(f"FAIL: LLM Tool Error: {e}")

async def test_mcp_connection():
    print("\n--- Test 3: MCP Direct Connection (SSE) ---")
    try:
        tools = await get_mcp_tools()
        print(f"Successfully retrieved {len(tools)} tools.")
        
        search_tool = next((t for t in tools if t.name == "search_products"), None)
        
        if search_tool:
            print("Executing search_products('camera')...")
            # In StructuredTool (LangChain), the coroutine is stored in the .coroutine attribute if async
            result = await search_tool.coroutine(query="camera")
            print(f"Result: {str(result)[:100]}...") 
            
            if "error" in str(result).lower() and "tool execution error" in str(result).lower():
                 print("FAIL: Tool returned an error.")
            else:
                 print("SUCCESS: MCP Tool Executed")
        else:
            print("FAIL: search_products tool not found.")
            
    except Exception as e:
        print(f"FAIL: MCP Error: {e}")

async def main():
    await test_llm_connection()
    await test_llm_tools()
    await test_mcp_connection()

if __name__ == "__main__":
    asyncio.run(main())
