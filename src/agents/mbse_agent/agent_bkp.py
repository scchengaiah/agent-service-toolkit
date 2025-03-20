from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command
from pydantic import BaseModel

from agents.mbse_agent.prompts import (
    MODEL_GENERATION_AGENT_SYSTEM_PROMPT,
    MODEL_VALIDATION_AGENT_SYSTEM_PROMPT,
    PLANNER_AGENT_SYSTEM_PROMPT,
    SAMPLE_REQUIREMENTS,
)
from agents.mbse_agent.state import (
    AgentState,
    ModelGenerationResponse,
    ModelValidationResponse,
    PlannerResponse,
)
from agents.mbse_agent.utils import get_azure_openai_model, get_bedrock_chat_model


def init_state(state: AgentState, config: RunnableConfig) -> AgentState:
    return {
        "requirements": SAMPLE_REQUIREMENTS,
        "no_of_allowed_feedback_iterations": 2,
        "current_iteration_count": 0,
    }


async def parse_claude_response(response: AIMessage, pydantic_model: BaseModel):
    if isinstance(response.content, list):
        # if response.content[0]["type"] == "thinking":
        #     thinking_content = response.content[0]["thinking"]
        content = response.content[1]["text"]
        parsed_response = PydanticOutputParser(pydantic_object=pydantic_model).parse(content)
        return parsed_response

    if isinstance(response.content, str):
        parsed_response = PydanticOutputParser(pydantic_object=pydantic_model).parse(
            response.content
        )
        return parsed_response

    raise ValueError("Response content is not a list or str.")


async def parse_openai_response(response: AIMessage, pydantic_model: BaseModel):
    if isinstance(response.content, str):
        parsed_response = PydanticOutputParser(pydantic_object=pydantic_model).parse(
            response.content
        )
        return parsed_response

    raise ValueError("Response content should be str.")


async def create_plan(state: AgentState, config: RunnableConfig) -> AgentState:
    """Model invocation"""

    # Get Bedrock Model
    model = get_bedrock_chat_model(
        model_name="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=8192,  # 8K tokens
        model_kwargs={
            "thinking": {
                "type": "enabled",
                "budget_tokens": 2048,
            },
        },
    )

    user_prompt = (
        "Generate a comprehensive plan for the following requirements.\n\n"
        "<Requirements>\n"
        f"{state['requirements']}\n"
        "</Requirements>"
    )

    # Prepare Messages
    sys_message = SystemMessage(content=PLANNER_AGENT_SYSTEM_PROMPT)

    user_message = HumanMessage(content=user_prompt)

    messages = [sys_message] + [user_message]

    # Invoke Model
    response = await model.ainvoke(messages, config)
    planner_response = await parse_claude_response(response, PlannerResponse)

    return {"planner_response": planner_response}


async def generate_sysml_model(state: AgentState, config: RunnableConfig) -> AgentState:
    model = get_bedrock_chat_model(
        model_name="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=102400,  # 100K tokens
    )

    if "model_validation_response" not in state or state["model_validation_response"] is None:
        user_prompt = (
            "Generate SysML V2 model for the following requirements based on the provided plan.\n\n"
            "<Requirements>\n"
            f"{state['requirements']}\n"
            "</Requirements>\n\n"
            "<Plan>\n"
            f"{state['planner_response'].plan}\n"
            "</Plan>"
        )
    elif state["model_validation_response"].validation_outcome == "invalid":
        user_prompt = (
            "Generate SysML V2 model for the following requirements based on the provided plan, previous model "
            "incorporating the feedback from the model validation agent.\n\n"
            "<Requirements>\n"
            f"{state['requirements']}\n"
            "</Requirements>\n\n"
            "<Plan>\n"
            f"{state['planner_response'].plan}\n"
            "</Plan>\n\n"
            "<Previous Model>\n"
            f"{state['model_generation_response'].model}\n"
            "</Previous Model>\n\n"
            "<Feedback>\n"
            f"{state['model_validation_response'].feedback}\n"
            "</Feedback>"
        )

    # Prepare Messages
    sys_message = SystemMessage(content=MODEL_GENERATION_AGENT_SYSTEM_PROMPT)
    user_message = HumanMessage(content=user_prompt)

    messages = [sys_message] + [user_message]

    response = await model.ainvoke(messages, config)
    model_generation_response = await parse_claude_response(response, ModelGenerationResponse)
    return {"model_generation_response": model_generation_response}


async def model_validation(state: AgentState, config: RunnableConfig) -> AgentState:
    model = get_bedrock_chat_model(
        model_name="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens=8192,  # 8K tokens
    )
    model = get_azure_openai_model(
        model_name="o3-mini",
        model_kwargs={"max_completion_tokens": 8192, "reasoning_effort": "high"},
    )
    user_prompt = (
        "Validate the SysML V2 model generated for the following requirements based on the provided plan.\n\n"
        "<Requirements>\n"
        f"{state['requirements']}\n"
        "</Requirements>\n\n"
        "<Plan>\n"
        f"{state['planner_response'].plan}\n"
        "</Plan>\n\n"
        "<SysML V2 Model>\n"
        f"{state['model_generation_response'].sysmlv2_notations}\n"
        "</SysML V2 Model>"
    )

    # Prepare Messages
    sys_message = SystemMessage(content=MODEL_VALIDATION_AGENT_SYSTEM_PROMPT)
    user_message = HumanMessage(content=user_prompt)

    messages = [sys_message] + [user_message]

    response = await model.ainvoke(messages, config)

    model_validation_response = await parse_openai_response(response, ModelValidationResponse)
    return {"model_validation_response": model_validation_response}


def check_model_validation_response(
    state: AgentState, config: RunnableConfig
) -> Command[Literal[END, "create_plan"]]:
    if state["model_validation_response"].validation_outcome == "valid":
        return Command(goto=END)

    if (
        state["model_validation_response"].validation_outcome == "invalid"
        and state["current_iteration_count"] < state["no_of_allowed_feedback_iterations"]
    ):
        return Command(
            goto="generate_sysml_model",
            update={"current_iteration_count": state["current_iteration_count"] + 1},
        )


# Define the graph
agent = StateGraph(AgentState)
agent.add_node(init_state, "init_state")
(agent.add_node(create_plan, "create_plan"),)
agent.add_node(generate_sysml_model, "generate_sysml_model")
agent.add_node(model_validation, "model_validation")

agent.set_entry_point("init_state")
agent.add_edge("init_state", "create_plan")
agent.add_edge("create_plan", "generate_sysml_model")
agent.add_edge("generate_sysml_model", "model_validation")
agent.add_conditional_edges(
    "model_validation", check_model_validation_response, [END, "generate_sysml_model"]
)

mbse_agent = agent.compile(checkpointer=MemorySaver())
mbse_agent.name = "MBSE Agent"
