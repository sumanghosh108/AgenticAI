"""
Domain Pack Interface — defines the contract for plug-and-play domain configurations.

Each domain pack bundles:
- Domain-specific prompts
- Tool configurations
- KPI definitions
- Scoring rubric dimensions
- Agent type mappings
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DomainPackConfig(BaseModel):
    """Configuration schema for a domain pack."""
    domain: str = Field(description="Domain identifier")
    display_name: str = Field(description="Human-readable domain name")
    tools: List[str] = Field(description="Tools available in this domain")
    metrics: List[str] = Field(description="Key metrics / KPIs for this domain")
    scoring_dimensions: List[str] = Field(description="Scoring rubric dimensions")
    agent_types: List[str] = Field(description="Agent types used in this domain")
    constraints: List[str] = Field(default_factory=list, description="Domain-specific constraints")


class BaseDomainPack(ABC):
    """Abstract base class for domain packs."""

    @abstractmethod
    def get_config(self) -> DomainPackConfig:
        """Return the domain configuration."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the domain-specific system prompt for the decision engine."""
        ...

    @abstractmethod
    def get_analysis_prompt(self, query: str, context: str) -> str:
        """Return a domain-tuned analysis prompt."""
        ...

    def get_tools(self) -> List[str]:
        """Return list of tools for this domain."""
        return self.get_config().tools

    def get_metrics(self) -> List[str]:
        """Return list of KPIs for this domain."""
        return self.get_config().metrics

    def get_scoring_dimensions(self) -> List[str]:
        """Return scoring rubric dimensions."""
        return self.get_config().scoring_dimensions

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the domain pack config."""
        return self.get_config().model_dump()
