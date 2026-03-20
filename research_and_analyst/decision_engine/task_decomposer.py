"""
Task Decomposition Engine — breaks user queries into structured execution plans.

Uses LLM to analyze the query, determine domain, identify required tools,
and produce an ordered list of sub-tasks with dependency tracking.
"""

import json
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage

from research_and_analyst.decision_engine.schemas import SubTask, TaskPlan
from research_and_analyst.logger import GLOBAL_LOGGER as log


TASK_DECOMPOSITION_PROMPT = """\
You are a strategic task planner for an AI decision system.

Given a user query, decompose it into a structured execution plan.

User Query: {query}
Domain Hint: {domain}

You must return VALID JSON matching this exact schema:
{{
  "goal": "<high-level objective>",
  "domain": "<finance|healthcare|general>",
  "tasks": [
    {{
      "id": 1,
      "description": "<what needs to be done>",
      "agent_type": "<research|finance|healthcare|general>",
      "tools_needed": ["web_search", "data_analyzer", ...],
      "depends_on": []
    }},
    ...
  ],
  "constraints": ["<any constraints or requirements>"]
}}

Rules:
1. Break complex queries into 3-7 atomic tasks.
2. Assign each task to the most appropriate agent_type.
3. Mark dependencies correctly — a task should only depend on tasks it actually needs output from.
4. Available tools: web_search, web_scraper, data_analyzer, document_parser, yfinance.
5. Order tasks so independent ones can run in parallel.
6. The final task should always be a synthesis/decision task.
7. For finance queries, include market data collection. For healthcare, include regulatory checks.

Return ONLY the JSON, no markdown code fences or explanation.
"""


class TaskDecomposer:
    """Decomposes user queries into structured task plans."""

    def __init__(self, llm=None):
        self.llm = llm

    def decompose(self, query: str, domain: str = "general") -> TaskPlan:
        """
        Decompose a query into a TaskPlan.

        Args:
            query: The user's input query.
            domain: Domain hint (finance, healthcare, general).

        Returns:
            TaskPlan with ordered sub-tasks.
        """
        if not self.llm:
            return self._fallback_decomposition(query, domain)

        prompt = TASK_DECOMPOSITION_PROMPT.format(query=query, domain=domain)

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            data = json.loads(raw)
            plan = TaskPlan(
                goal=data.get("goal", query),
                domain=data.get("domain", domain),
                tasks=[SubTask(**t) for t in data.get("tasks", [])],
                constraints=data.get("constraints", []),
            )

            log.info(
                "Task decomposition complete",
                goal=plan.goal,
                task_count=len(plan.tasks),
                domain=plan.domain,
            )
            return plan

        except (json.JSONDecodeError, Exception) as e:
            log.warning("LLM decomposition failed, using fallback", error=str(e))
            return self._fallback_decomposition(query, domain)

    def _fallback_decomposition(self, query: str, domain: str) -> TaskPlan:
        """Produce a reasonable default plan when LLM is unavailable."""
        tasks = [
            SubTask(
                id=1,
                description=f"Research: {query}",
                agent_type="research",
                tools_needed=["web_search", "web_scraper"],
                depends_on=[],
            ),
            SubTask(
                id=2,
                description=f"Analyze collected data for: {query}",
                agent_type=domain if domain != "general" else "research",
                tools_needed=["data_analyzer"],
                depends_on=[1],
            ),
            SubTask(
                id=3,
                description=f"Generate decision and recommendations for: {query}",
                agent_type="general",
                tools_needed=[],
                depends_on=[1, 2],
            ),
        ]

        return TaskPlan(
            goal=query,
            domain=domain,
            tasks=tasks,
            constraints=["Use available data only", "Cite sources"],
        )

    def get_execution_order(self, plan: TaskPlan) -> list[list[int]]:
        """
        Compute parallel execution layers from task dependencies.

        Returns list of lists — each inner list contains task IDs that can run in parallel.
        """
        completed = set()
        remaining = {t.id: set(t.depends_on) for t in plan.tasks}
        layers = []

        while remaining:
            # Find tasks whose dependencies are all completed
            ready = [tid for tid, deps in remaining.items() if deps.issubset(completed)]
            if not ready:
                # Circular dependency — break by forcing remaining
                log.warning("Circular dependency detected, forcing remaining tasks")
                ready = list(remaining.keys())

            layers.append(ready)
            for tid in ready:
                completed.add(tid)
                del remaining[tid]

            # Update remaining dependencies
            for deps in remaining.values():
                deps -= completed

        return layers
