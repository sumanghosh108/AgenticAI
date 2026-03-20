"""
Base Agent Interface — abstract contract for all plug-and-play agents.

Every domain agent (research, finance, healthcare, etc.) must implement
this interface. The execution graph routes tasks to agents through this
common protocol.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from research_and_analyst.logger import GLOBAL_LOGGER as log


class AgentResult(BaseModel):
    """Standardised output from any agent."""
    agent_name: str
    agent_type: str
    task_description: str
    output: str = ""
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    sources_used: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    tokens_used: int = 0
    success: bool = True
    error: str = ""


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.

    Subclasses must implement:
        - execute(task, context) -> AgentResult
        - available_tools() -> list of tool names

    Optionally override:
        - validate_task(task) -> bool
        - post_process(result) -> AgentResult
    """

    def __init__(self, name: str, agent_type: str, llm=None):
        self.name = name
        self.agent_type = agent_type
        self.llm = llm
        log.info("Agent initialized", agent=name, type=agent_type)

    @abstractmethod
    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute a task and return structured results."""
        ...

    @abstractmethod
    def available_tools(self) -> List[str]:
        """Return list of tool names this agent can use."""
        ...

    def validate_task(self, task: str) -> bool:
        """Check if this agent can handle the given task. Override for specialization."""
        return True

    def post_process(self, result: AgentResult) -> AgentResult:
        """Optional post-processing hook. Override to transform results."""
        return result

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Full execution pipeline: validate → execute → post-process."""
        if not self.validate_task(task):
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                task_description=task,
                success=False,
                error=f"Agent '{self.name}' cannot handle this task type.",
            )

        try:
            log.info("Agent executing task", agent=self.name, task=task[:100])
            result = self.execute(task, context)
            result = self.post_process(result)
            log.info("Agent task completed", agent=self.name, success=result.success)
            return result
        except Exception as e:
            log.error("Agent execution failed", agent=self.name, error=str(e))
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                task_description=task,
                success=False,
                error=str(e),
            )
