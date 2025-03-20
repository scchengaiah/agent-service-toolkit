from typing import Literal

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class PlannerResponse(BaseModel):
    requirements_summary: str = Field(description="Summary of the requirements")
    plan: str = Field(description="Comprehensive plan for implementing the requirements")
    feedback_notes: str = Field(
        description="Feedback notes if applicable and provided by the Model Validation Agent or End User or both else it will be empty"
    )


class ModelGenerationResponse(BaseModel):
    sysmlv2_notations: str = Field(description="SysMLv2 textual notations")
    comments: str = Field(description="Comments on the notations")


class ModelValidationResponse(BaseModel):
    validation_outcome: Literal["valid", "invalid"] = Field(description="Outcome of the validation")
    validation_comments: str = Field(description="Comments on the validation performed")
    feedback: str = Field(description="Feedback for the planner agent for generating updated plan")


class AgentState(MessagesState, total=False):
    requirements: str
    no_of_allowed_feedback_iterations: int
    current_iteration_count: int
    planner_response: PlannerResponse
    model_generation_response: ModelGenerationResponse
    model_validation_response: ModelValidationResponse
