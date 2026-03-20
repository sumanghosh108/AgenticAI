"""
Pydantic models and TypedDict states for the multi-step decision system.

Covers: task decomposition, decisions, critiques, source scoring,
KPI extraction, and the main decision workflow graph state.
"""

import operator
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Task Decomposition
# ─────────────────────────────────────────────

class SubTask(BaseModel):
    """A single decomposed sub-task."""
    id: int = Field(description="Sequential task identifier")
    description: str = Field(description="What needs to be done")
    agent_type: str = Field(description="Which agent handles this (research, finance, healthcare, general)")
    tools_needed: List[str] = Field(default_factory=list, description="Tools required for this task")
    depends_on: List[int] = Field(default_factory=list, description="IDs of tasks this depends on")


class TaskPlan(BaseModel):
    """Structured plan produced by the Task Decomposition Engine."""
    goal: str = Field(description="High-level objective")
    domain: str = Field(default="general", description="Domain context (finance, healthcare, general)")
    tasks: List[SubTask] = Field(description="Ordered list of sub-tasks")
    constraints: List[str] = Field(default_factory=list, description="Constraints or requirements")


# ─────────────────────────────────────────────
# Decision Engine
# ─────────────────────────────────────────────

class ScoringDimension(BaseModel):
    """A single dimension in the scoring rubric."""
    name: str = Field(description="Dimension name (e.g. 'growth_potential')")
    score: float = Field(ge=0.0, le=1.0, description="Score between 0 and 1")
    reasoning: str = Field(description="Why this score was assigned")


class Decision(BaseModel):
    """Structured decision output from the Decision Engine."""
    decision: str = Field(description="The recommended action (e.g. 'Invest', 'Hold', 'Reject')")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence score")
    reasons: List[str] = Field(description="Key reasons supporting the decision")
    risks: List[str] = Field(default_factory=list, description="Identified risks")
    scoring: List[ScoringDimension] = Field(default_factory=list, description="Detailed scoring breakdown")
    alternatives: List[str] = Field(default_factory=list, description="Alternative actions considered")


# ─────────────────────────────────────────────
# Critique & Self-Evaluation
# ─────────────────────────────────────────────

class CritiqueResult(BaseModel):
    """Output from a single critic agent."""
    critic_type: str = Field(description="Type of critic (fact_checker, bias_detector, logic_validator)")
    score: float = Field(ge=0.0, le=10.0, description="Quality score out of 10")
    issues: List[str] = Field(default_factory=list, description="Identified problems")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    verified_claims: List[str] = Field(default_factory=list, description="Claims verified as accurate")
    unverified_claims: List[str] = Field(default_factory=list, description="Claims that could not be verified")


class AggregatedCritique(BaseModel):
    """Combined output from the multi-critic system."""
    overall_score: float = Field(ge=0.0, le=10.0, description="Weighted average quality score")
    critiques: List[CritiqueResult] = Field(description="Individual critic results")
    pass_threshold: bool = Field(description="Whether the output meets quality bar")
    revision_needed: bool = Field(description="Whether another refinement iteration is needed")


# ─────────────────────────────────────────────
# Source Reliability
# ─────────────────────────────────────────────

class SourceScore(BaseModel):
    """Credibility assessment for an information source."""
    source: str = Field(description="Source URL or identifier")
    credibility: float = Field(ge=0.0, le=1.0, description="Credibility score")
    domain_authority: str = Field(default="unknown", description="Domain authority tier (high, medium, low, unknown)")
    citation_frequency: int = Field(default=0, description="How many times this source was cited")
    reasoning: str = Field(default="", description="Why this credibility score was assigned")


# ─────────────────────────────────────────────
# KPI Extraction
# ─────────────────────────────────────────────

class KPI(BaseModel):
    """A single extracted key performance indicator."""
    name: str = Field(description="KPI name (e.g. 'Revenue Growth', 'CAC', 'LTV')")
    value: str = Field(description="Extracted value with units")
    period: str = Field(default="", description="Time period this KPI covers")
    source: str = Field(default="", description="Where this KPI was extracted from")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5, description="Extraction confidence")


class KPIReport(BaseModel):
    """Collection of extracted KPIs."""
    entity: str = Field(description="Company or entity the KPIs describe")
    kpis: List[KPI] = Field(description="Extracted KPIs")
    summary: str = Field(default="", description="Brief narrative summary of KPI picture")


# ─────────────────────────────────────────────
# Enterprise Report
# ─────────────────────────────────────────────

class EnterpriseReport(BaseModel):
    """Structured enterprise-grade report output."""
    executive_summary: str = Field(description="1-2 paragraph executive summary")
    key_insights: List[str] = Field(description="Bulleted key insights")
    risks: List[str] = Field(description="Identified risks")
    recommendations: List[str] = Field(description="Actionable recommendations")
    kpis: Optional[KPIReport] = Field(default=None, description="Extracted KPIs if applicable")
    sources: List[SourceScore] = Field(default_factory=list, description="Scored sources used")
    decision: Optional[Decision] = Field(default=None, description="Final decision if applicable")


# ─────────────────────────────────────────────
# Refinement Tracking
# ─────────────────────────────────────────────

class RefinementVersion(BaseModel):
    """Tracks a single iteration of the refinement loop."""
    iteration: int = Field(description="Iteration number")
    content: str = Field(description="Content at this version")
    critique: Optional[AggregatedCritique] = Field(default=None, description="Critique of this version")
    token_usage: int = Field(default=0, description="Tokens consumed in this iteration")


# ─────────────────────────────────────────────
# Main Decision Workflow State (LangGraph)
# ─────────────────────────────────────────────

class DecisionGraphState(TypedDict):
    """State flowing through the decision workflow LangGraph."""

    # Input
    query: str
    domain: str
    max_iterations: int
    wf_task_id: str  # Task ID for progress broadcasting

    # Task Decomposition
    task_plan: Optional[TaskPlan]

    # Agent Outputs (accumulated)
    agent_outputs: Annotated[List[Dict[str, Any]], operator.add]

    # Memory
    short_term_memory: Dict[str, Any]
    long_term_context: List[str]

    # Cross-Verification
    verification_report: Optional[Dict[str, Any]]
    verification_summary: str

    # Decision
    decision: Optional[Decision]

    # Critique & Refinement
    critiques: Annotated[List[CritiqueResult], operator.add]
    aggregated_critique: Optional[AggregatedCritique]
    refinement_history: List[RefinementVersion]
    current_iteration: int

    # Business Intelligence
    sources: List[SourceScore]
    kpis: Optional[KPIReport]

    # Final Output
    enterprise_report: Optional[EnterpriseReport]
    final_output: str
    status: str
