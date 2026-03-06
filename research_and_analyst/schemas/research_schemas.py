"""
Schemas for the Autonomous Research Report Generator.

Defines Pydantic models and TypedDict state classes used across
the interview and report-generation LangGraph workflows.
"""

import operator
from typing import Annotated, List, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage


# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class Analyst(BaseModel):
    """A research analyst persona created by the LLM."""

    name: str = Field(description="Full name of the analyst")
    role: str = Field(description="Role or title of the analyst")
    affiliation: str = Field(
        description="Organisation or institution the analyst is affiliated with"
    )
    description: str = Field(
        description="A brief description of the analyst's focus area, "
                    "expertise, and the perspective they bring to the research"
    )

    @property
    def persona(self) -> str:
        return (
            f"Name: {self.name}\n"
            f"Role: {self.role}\n"
            f"Affiliation: {self.affiliation}\n"
            f"Focus: {self.description}\n"
        )


class Perspectives(BaseModel):
    """A collection of analyst personas returned by the LLM."""

    analysts: List[Analyst] = Field(
        description="List of analyst personas for the research topic"
    )


# ─────────────────────────────────────────────
# TypedDict States (LangGraph graph state)
# ─────────────────────────────────────────────

class InterviewState(TypedDict):
    """State flowing through the interview sub-graph."""

    analyst: Analyst
    messages: Annotated[List[AnyMessage], operator.add]
    max_num_turns: int
    context: Annotated[List[str], operator.add]
    interview: str
    sections: List[str]


class ResearchGraphState(TypedDict):
    """State for the outer report-generation graph."""

    topic: str
    max_analysts: int
    analysts: List[Analyst]
    human_analyst_feedback: str
    sections: Annotated[List[str], operator.add]
    introduction: str
    content: str
    conclusion: str
    final_report: str
