from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph

from agents.mbse_agent.prompts import DEFAULT_SYSTEM_PROMPT
from core import get_model, settings


class AgentState(MessagesState, total=False):
    pass


async def model(state: AgentState, config: RunnableConfig) -> AgentState:
    """Model invocation"""

    # Get Model
    model = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))

    # Prepare Messages
    sys_message = SystemMessage(content=DEFAULT_SYSTEM_PROMPT)
    messages = [sys_message] + state["messages"]

    # Invoke Model
    response = await model.ainvoke(messages, config)

    return {"messages": [AIMessage(content=response.content)]}


# Define the graph
agent = StateGraph(AgentState)
agent.add_node(model, "model")

agent.set_entry_point("model")
agent.add_edge("model", END)

mbse_agent = agent.compile(checkpointer=MemorySaver())
mbse_agent.name = "MBSE Agent"
