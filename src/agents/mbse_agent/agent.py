from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from agents.mbse_agent.state import (
    AgentState,
    ModelGenerationResponse,
    ModelValidationResponse,
    PlannerResponse,
)


def init_state(state: AgentState, config: dict) -> AgentState:
    return {
        "requirements": "Mock requirements",
        "no_of_allowed_feedback_iterations": 2,
        "current_iteration_count": 0,
    }


async def create_plan(state: AgentState, config: dict) -> AgentState:
    # Mock planner response
    planner_response = PlannerResponse(
        requirements_summary="Summary of mock requirements",
        plan="Mock plan for system design",
        feedback_notes="",  # Empty as no feedback yet
    )
    return {"planner_response": planner_response}


async def generate_sysml_model(state: AgentState, config: dict) -> AgentState:
    # Mock model generation response
    model_response = ModelGenerationResponse(
        sysmlv2_notations="package 'MockSystem' { ... }",  # Mock SysMLv2 notation
        comments="Generated basic system structure",
    )
    return {"model_generation_response": model_response}


async def model_validation(state: AgentState, config: dict) -> AgentState:
    # Simulate validation - first attempt invalid, second attempt valid
    is_valid = state["current_iteration_count"] >= 1

    validation_response = ModelValidationResponse(
        validation_outcome="valid" if is_valid else "invalid",
        validation_comments="Performed structural and semantic validation",
        feedback=(
            "Model needs improvements in component interfaces"
            if not is_valid
            else "Model meets all requirements"
        ),
    )
    return {"model_validation_response": validation_response}


def check_model_validation_response(
    state: AgentState, config: dict
) -> Command[Literal[END, "generate_sysml_model"]]:
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


# Define the mock graph
mock_agent = StateGraph(AgentState)
mock_agent.add_node(init_state, "init_state")
mock_agent.add_node(create_plan, "create_plan")
mock_agent.add_node(generate_sysml_model, "generate_sysml_model")
mock_agent.add_node(model_validation, "model_validation")

mock_agent.set_entry_point("init_state")
mock_agent.add_edge("init_state", "create_plan")
mock_agent.add_edge("create_plan", "generate_sysml_model")
mock_agent.add_edge("generate_sysml_model", "model_validation")
mock_agent.add_conditional_edges(
    "model_validation", check_model_validation_response, [END, "generate_sysml_model"]
)

mbse_agent = mock_agent.compile(checkpointer=MemorySaver())
