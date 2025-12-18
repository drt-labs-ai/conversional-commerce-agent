import os
import operator
from typing import Annotated, Sequence, TypedDict, Union, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, FunctionMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import Tool

from sap_client import get_mcp_tools
from product_search import search_products_vector

# State Definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str

# LLM Setup
llm = ChatOpenAI(
    base_url=os.getenv("LLM_BASE_URL", "http://host.docker.internal:1234/v1"),
    api_key="lm-studio",
    model=os.getenv("MODEL_NAME", "mistral-7b-instruct-v0.3"),
    temperature=0
)

# --- Agents Setup ---

async def create_agent_graph():
    # 1. Load Tools
    mcp_tools = await get_mcp_tools()
    
    # RAG Tool
    from langchain_core.tools import StructuredTool

    # RAG Tool
    async def vector_search(query: str):
        """Search for products using semantic vector search."""
        return search_products_vector(query)
    
    rag_tool = StructuredTool.from_function(
        coroutine=vector_search,
        name="vector_search",
        description="Search for products using semantic vector search. Good for descriptions."
    )
    
    # Split tools
    search_tools = [t for t in mcp_tools if "search" in t.name or "details" in t.name] + [rag_tool]
    cart_tools = [t for t in mcp_tools if "cart" in t.name or "order" in t.name]

    # 2. Agent Nodes
    
    # Helper to create an agent node
    def create_agent_node(agent_name: str, tools: List[Tool], system_prompt: str):
        prompt = ChatPromptTemplate.from_messages([
            ("user", f"System Instructions: {system_prompt}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # We bind tools to the LLM
        agent_runnable = prompt | llm.bind_tools(tools)
        
        async def agent_node(state):
            try:
                # Trim messages to last 6 to fit in context
                input_messages = state["messages"][-6:]
                print(f"DEBUG: {agent_name} Input Messages: {len(input_messages)}")
                result = await agent_runnable.ainvoke({"messages": input_messages})
                print(f"DEBUG: {agent_name} raw output: {result.content[:50]}...")
                return {"messages": [result]}
            except Exception as e:
                error_msg = f"Error executing agent logic: {str(e)}"
                return {"messages": [AIMessage(content=error_msg)]}
            
        return agent_node, tools

    # Search Agent
    search_agent_node, search_tools_list = create_agent_node(
        "SearchAgent", 
        search_tools,
        "You are a Product Search Specialist. Use vector_search for vague queries and search_products for specific ones. "
        "Provide product details when asked. If the user wants to buy, refer them to the CartAgent."
    )

    # Cart Agent
    cart_agent_node, cart_tools_list = create_agent_node(
        "CartAgent",
        cart_tools,
        "You are a Cart and Checkout Specialist. specialized in managing the shopping cart. "
        "You can create carts, add items, view cart, and place orders. "
        "Always confirm details before placing an order."
    )
    
    # Revised Router (Text-based for safety with generic Ollama models)
    router_prompt = ChatPromptTemplate.from_messages([
        ("user", "You are the supervisor. You have workers: SearchAgent, CartAgent. \n"
         "User Request: {recent_messages} \n"
         "Decide who should act next.\n"
         "1. If the user wants to search for products or get details -> SearchAgent\n"
         "2. If the user wants to manage cart or checkout -> CartAgent\n"
         "3. If the answer is provided or conversation is over -> FINISH\n"
         "Return ONLY the name: SearchAgent or CartAgent or FINISH."),
    ])
    
    # Simple chain that returns the raw message content
    router_chain = router_prompt | llm 

    async def supervisor_node(state):
        messages = state["messages"]
        # Trim messages for supervisor too
        recent_messages = messages[-6:]
        
        # We need to format messages to string or pass them as is if prompt expects it
        response = await router_chain.ainvoke({"recent_messages": recent_messages})
        text = response.content.strip()
        print(f"DEBUG: Supervisor Decision: {text}")
        
        if "SearchAgent" in text:
            return {"next": "SearchAgent"}
        elif "CartAgent" in text:
            return {"next": "CartAgent"}
        else:
            return {"next": "FINISH"}

    # 4. Build Graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("SearchAgent", search_agent_node)
    workflow.add_node("CartAgent", cart_agent_node)
    
    # Tool Nodes
    # Note: StateGraph with tool calling usually requires a ToolNode object to execute the tool calls returned by the Agent.
    # Our `agent_node` above just returns the AIMessage. If that AIMessage has tool_calls, we need a node to execute them.
    # We need to restructure slightly to support tool execution loop within the agent or as separate nodes.
    # The standard LangGraph "Agent" pattern uses a "tools" node.
    
    search_tool_node = ToolNode(search_tools_list)
    cart_tool_node = ToolNode(cart_tools_list)
    
    workflow.add_node("SearchTools", search_tool_node)
    workflow.add_node("CartTools", cart_tool_node)

    workflow.set_entry_point("Supervisor")
    
    # Conditional edges for Supervisor
    workflow.add_conditional_edges(
        "Supervisor",
        lambda x: x["next"],
        {
            "SearchAgent": "SearchAgent",
            "CartAgent": "CartAgent",
            "FINISH": END
        }
    )
    
    # Logic for Agents: Agent -> [Tools] -> Agent
    
    def should_continue(state):
        messages = state['messages']
        last_message = messages[-1]
        if last_message.tool_calls:
            return "continue"
        return "end"

    # Search Logic
    workflow.add_conditional_edges(
        "SearchAgent",
        should_continue,
        {
            "continue": "SearchTools",
            "end": "Supervisor" # Return control to Supervisor after answering
        }
    )
    workflow.add_edge("SearchTools", "SearchAgent") # Loop back to agent to interpret tool output

    # Cart Logic
    workflow.add_conditional_edges(
        "CartAgent",
        should_continue,
        {
            "continue": "CartTools",
            "end": "Supervisor"
        }
    )
    workflow.add_edge("CartTools", "CartAgent")

    # Persistence
    from langgraph.checkpoint.memory import MemorySaver
    # using MemorySaver for simplicity in this artifact, but can be swapped for RedisSaver
    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)
