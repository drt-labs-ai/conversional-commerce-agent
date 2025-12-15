import os
import operator
from typing import Annotated, Sequence, TypedDict, Union, List

from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, FunctionMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import Tool

from mcp_client_utils import get_mcp_tools
from rag_utils import search_products_vector

# State Definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str

# LLM Setup
llm = ChatOllama(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
    model=os.getenv("MODEL_NAME", "llama3"),
    temperature=0
)

# --- Agents Setup ---

async def create_agent_graph():
    # 1. Load Tools
    mcp_tools = await get_mcp_tools()
    
    # RAG Tool
    async def rag_search(query: str):
        return search_products_vector(query)
    
    rag_tool = Tool(
        name="vector_search",
        func=None,
        coroutine=rag_search,
        description="Search for products using semantic vector search. Good for descriptions."
    )
    
    # Split tools
    search_tools = [t for t in mcp_tools if "search" in t.name or "details" in t.name] + [rag_tool]
    cart_tools = [t for t in mcp_tools if "cart" in t.name or "order" in t.name]

    # 2. Agent Nodes
    
    # Helper to create an agent node
    def create_agent_node(agent_name: str, tools: List[Tool], system_prompt: str):
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])
        # We bind tools to the LLM
        agent_runnable = prompt | llm.bind_tools(tools)
        
        async def agent_node(state):
            result = await agent_runnable.ainvoke(state)
            return {"messages": [result]}
            
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
    
    # 3. Supervisor / Router
    # A simple router LLM that decides who to call next
    
    members = ["SearchAgent", "CartAgent"]
    
    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        " following workers: {members}. Given the following user request,"
        " respond with the worker to act next. Each worker will perform a"
        " task and respond with their results and status. When finished with questions about products,"
        " allow the user to continue shopping or checkout.\n"
        "If the user is asking a general question or the task is finished, respond with FINISH."
    )
    
    options = ["FINISH"] + members
    
    function_def = {
        "name": "route",
        "description": "Select the next role.",
        "parameters": {
            "title": "routeSchema",
            "type": "object",
            "properties": {
                "next": {
                    "title": "Next",
                    "anyOf": [
                        {"enum": options},
                    ],
                }
            },
            "required": ["next"],
        },
    }
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        (
            "system",
            "Given the conversation above, who should act next? "
            "Or should we FINISH? Select one of: {options}",
        ),
    ]).partial(options=str(options), members=", ".join(members))

    supervisor_chain = (
        prompt 
        | llm.bind_functions(functions=[function_def], function_call="route") 
        | (lambda x: x.additional_kwargs["function_call"]["arguments"]) # JSON output parser might be better
    )

    # Note: Ollama JSON/Function calling output needs careful parsing. 
    # For stability with Llama3 (which isn't native function calling aligned like OpenAI), 
    # we might use a structured outputparser or just simple text prompting.
    # Let's switch to a structured router for robustness if Llama3 func calling is flaky.
    
    # Revised Router (Text-based for safety with generic Ollama models)
    router_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the supervisor. You have workers: SearchAgent, CartAgent. \n"
         "User Request: {messages} \n"
         "Who should act next? Return ONLY the name: SearchAgent or CartAgent. "
         "If the answer is provided or conversation is over, return FINISH."),
    ])
    
    router_chain = router_prompt | llm 

    async def supervisor_node(state):
        # Taking the last message to decide, or full history
        # For simplicity, we just invoke the router.
        messages = state["messages"]
        last_message = messages[-1]
        
        # Simple heuristic or LLM-based routing
        # "I want to buy..." -> CartAgent
        # "Show me drills..." -> SearchAgent
        
        response = await router_chain.ainvoke({"messages": messages})
        text = response.content.strip()
        
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
