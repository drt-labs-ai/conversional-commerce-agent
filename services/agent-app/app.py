import chainlit as cl
from agent_logic import create_agent_graph
from langchain_core.messages import HumanMessage

@cl.on_chat_start
async def on_chat_start():
    app = await create_agent_graph()
    cl.user_session.set("app", app)
    cl.user_session.set("config", {"configurable": {"thread_id": cl.user_session.get("id")}, "recursion_limit": 100})
    
    await cl.Message(content="Hello! I am your Conversational Commerce Assistant. How can I help you today?").send()

@cl.on_message
async def on_message(message: cl.Message):
    app = cl.user_session.get("app")
    config = cl.user_session.get("config")
    
    # Run the graph
    inputs = {"messages": [HumanMessage(content=message.content)]}
    
    async for event in app.astream(inputs, config=config):
        # We can stream intermediate outputs if desired
        pass
        
    # Get final state
    # Ideally we should stream the response from the last agent
    # For now, let's just get the last message from the state
    snapshot = await app.aget_state(config)
    if snapshot and snapshot.values and "messages" in snapshot.values:
        last_msg = snapshot.values["messages"][-1]
        await cl.Message(content=last_msg.content).send()
    else:
        # Fallback if specific streaming didn't output
        # Usually looking at the event stream is better for real-time feedback
        # But for quick prototype:
        await cl.Message(content="Task completed.").send()
