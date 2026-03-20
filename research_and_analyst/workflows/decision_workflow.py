"""
Decision Workflow — Main LangGraph execution graph for the multi-step decision system.

Orchestrates:
1. Task Decomposition → structured plan
2. Agent Dispatch → parallel/sequential agent execution
3. Decision Engine → structured decision with scoring
4. Critique & Refinement → iterative quality improvement
5. Business Intelligence → KPI extraction, source scoring, enterprise report

Graph Flow:
    START → decompose_task → dispatch_agents → generate_decision
        → critique_output → (conditional) → refine_or_finalize
        → extract_kpis → score_sources → format_report → END

Features:
    - Conditional routing based on critique scores
    - Retry loops for failed agent tasks
    - Parallel agent dispatch for independent tasks
    - Token budget tracking
    - Human-in-the-loop interrupt support
"""

import json
import time
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from research_and_analyst.decision_engine.schemas import (
    AggregatedCritique,
    CritiqueResult,
    Decision,
    DecisionGraphState,
    EnterpriseReport,
    RefinementVersion,
    TaskPlan,
)
from research_and_analyst.decision_engine.task_decomposer import TaskDecomposer
from research_and_analyst.decision_engine.decision_maker import DecisionMaker
from research_and_analyst.agents.research_agent import ResearchAgent
from research_and_analyst.agents.finance_agent import FinanceAgent
from research_and_analyst.agents.healthcare_agent import HealthcareAgent
from research_and_analyst.agents.critic_agent import CriticAgent
from research_and_analyst.memory.short_term import ShortTermMemory
from research_and_analyst.memory.long_term import LongTermMemory
from research_and_analyst.refinement.iterative_loop import IterativeRefinementLoop, RefinementConfig
from research_and_analyst.critique.quality_scorer import QualityScorer
from research_and_analyst.business_intel.source_scorer import SourceReliabilityScorer
from research_and_analyst.business_intel.kpi_extractor import KPIExtractor
from research_and_analyst.business_intel.report_formatter import ReportFormatter
from research_and_analyst.domain_packs.base_pack import BaseDomainPack
from research_and_analyst.domain_packs.finance_pack import FinanceDomainPack
from research_and_analyst.domain_packs.healthcare_pack import HealthcareDomainPack
from research_and_analyst.utils.model_loader import ModelLoader
from research_and_analyst.logger import GLOBAL_LOGGER as log
from research_and_analyst.job_queue.websocket_manager import broadcast_progress


# ─────────────────────────────────────────────
# Domain Pack Registry
# ─────────────────────────────────────────────

DOMAIN_PACKS: Dict[str, BaseDomainPack] = {
    "finance": FinanceDomainPack(),
    "healthcare": HealthcareDomainPack(),
}

# ─────────────────────────────────────────────
# Agent Registry
# ─────────────────────────────────────────────

AGENT_REGISTRY = {
    "research": ResearchAgent,
    "finance": FinanceAgent,
    "healthcare": HealthcareAgent,
}


class DecisionWorkflowBuilder:
    """
    Builds and manages the LangGraph decision workflow.

    Usage:
        builder = DecisionWorkflowBuilder()
        graph = builder.build()
        result = builder.run("Analyze AI startup market", domain="finance")
    """

    def __init__(self):
        loader = ModelLoader()
        self.llm = loader.load_llm()
        self.memory_saver = MemorySaver()

        # Core engines
        self.decomposer = TaskDecomposer(llm=self.llm)
        self.decision_maker = DecisionMaker(llm=self.llm)
        self.quality_scorer = QualityScorer(llm=self.llm)
        self.source_scorer = SourceReliabilityScorer()
        self.kpi_extractor = KPIExtractor(llm=self.llm)
        self.report_formatter = ReportFormatter()

        # Memory
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

        # Compiled graph
        self._graph = None

    # ─────────────────────────────────────────
    # Graph Nodes
    # ─────────────────────────────────────────

    def decompose_task(self, state: DecisionGraphState) -> Dict[str, Any]:
        """Node: Decompose user query into a structured task plan."""
        query = state["query"]
        domain = state.get("domain", "general")

        log.info("Decomposing task", query=query[:100], domain=domain)

        # Check long-term memory for similar past queries
        past_context = []
        try:
            past_context = self.long_term.get_relevant_context(query, n_results=2)
        except Exception:
            pass  # Long-term memory may not be initialized

        plan = self.decomposer.decompose(query, domain)

        # Store in short-term memory
        self.short_term.store("task_plan", plan.model_dump(), source="decomposer", entry_type="plan")

        return {
            "task_plan": plan,
            "long_term_context": past_context,
            "status": "tasks_decomposed",
        }

    def dispatch_agents(self, state: DecisionGraphState) -> Dict[str, Any]:
        """Node: Dispatch tasks to appropriate agents and collect results."""
        plan = state["task_plan"]
        domain = state.get("domain", "general")
        wf_task_id = state.get("wf_task_id", "")

        if not plan:
            return {"agent_outputs": [], "status": "no_plan"}

        # Get execution order (parallel layers)
        execution_layers = self.decomposer.get_execution_order(plan)
        all_outputs = []

        # Get domain pack for context
        domain_pack = DOMAIN_PACKS.get(domain)

        # Build flat list of all tasks for counting
        all_task_ids = [tid for layer in execution_layers for tid in layer]
        total_agents = len(all_task_ids)

        # Build agent info list for the frontend
        agents_info = []
        for tid in all_task_ids:
            t = next((t for t in plan.tasks if t.id == tid), None)
            if t:
                agents_info.append({
                    "id": tid,
                    "name": t.agent_type.replace("_", " ").title() + " Agent",
                    "type": t.agent_type,
                    "task": t.description[:120],
                    "status": "pending",
                })

        def _update_agent_meta(pct, completed):
            """Update both WebSocket and task queue with agent progress."""
            details = {
                "agents": agents_info,
                "total_agents": total_agents,
                "completed_agents": completed,
            }
            broadcast_progress(wf_task_id, "dispatch_agents", pct, "running", details)
            try:
                from research_and_analyst.api.routes.api_routes import _get_task_queue
                queue = _get_task_queue()
                with queue._lock:
                    state = queue._tasks.get(wf_task_id)
                    if state:
                        state.current_step = "dispatch_agents"
                        state.progress_pct = pct
                        state.metadata.update(details)
            except Exception:
                pass

        # Broadcast initial agent roster
        if wf_task_id:
            _update_agent_meta(15.0, 0)

        completed_count = 0

        for layer_idx, task_ids in enumerate(execution_layers):
            log.info("Executing task layer", layer=layer_idx, tasks=task_ids)

            for task_id in task_ids:
                # Find the task
                task = next((t for t in plan.tasks if t.id == task_id), None)
                if not task:
                    continue

                # Mark agent as running
                for a in agents_info:
                    if a["id"] == task_id:
                        a["status"] = "running"

                if wf_task_id:
                    _update_agent_meta(15.0 + (completed_count / max(total_agents, 1)) * 30.0, completed_count)

                # Get or create the appropriate agent
                agent_cls = AGENT_REGISTRY.get(task.agent_type, ResearchAgent)
                agent = agent_cls(llm=self.llm)

                # Build context from prior outputs and memory
                context = {
                    "additional_context": self.short_term.get_context_summary(),
                    "domain": domain,
                }
                if domain_pack:
                    context["domain_prompt"] = domain_pack.get_system_prompt()

                # Execute agent
                result = agent.run(task.description, context=context)

                # Store result in short-term memory
                self.short_term.store(
                    f"agent_output_{task_id}",
                    result.output,
                    source=result.agent_name,
                    entry_type="agent_output",
                )

                all_outputs.append(result.model_dump())
                completed_count += 1

                # Mark agent as completed/failed
                for a in agents_info:
                    if a["id"] == task_id:
                        a["status"] = "completed" if result.success else "failed"

                if wf_task_id:
                    _update_agent_meta(15.0 + (completed_count / max(total_agents, 1)) * 30.0, completed_count)

                log.info(
                    "Agent completed task",
                    agent=result.agent_name,
                    task_id=task_id,
                    success=result.success,
                )

        return {"agent_outputs": all_outputs, "status": "agents_completed"}

    def generate_decision(self, state: DecisionGraphState) -> Dict[str, Any]:
        """Node: Generate structured decision from agent outputs."""
        query = state["query"]
        domain = state.get("domain", "general")
        agent_outputs = state.get("agent_outputs", [])

        # Get domain-specific constraints and rubric
        domain_pack = DOMAIN_PACKS.get(domain)
        constraints = None
        rubric = None
        if domain_pack:
            config = domain_pack.get_config()
            constraints = config.constraints
            rubric = config.scoring_dimensions

        decision = self.decision_maker.decide(
            query=query,
            agent_outputs=agent_outputs,
            domain=domain,
            constraints=constraints,
            custom_rubric=rubric,
        )

        self.short_term.store("decision", decision.model_dump(), source="decision_maker", entry_type="decision")

        return {"decision": decision, "status": "decision_generated"}

    def critique_output(self, state: DecisionGraphState) -> Dict[str, Any]:
        """Node: Run multi-critic evaluation on the generated output."""
        decision = state.get("decision")
        agent_outputs = state.get("agent_outputs", [])

        # Build content to critique
        content_parts = []
        if decision:
            content_parts.append(f"Decision: {decision.decision} (Confidence: {decision.confidence})")
            content_parts.append(f"Reasons: {', '.join(decision.reasons)}")
        for out in agent_outputs:
            content_parts.append(out.get("output", "")[:1000])

        content = "\n\n".join(content_parts)
        sources = []
        for out in agent_outputs:
            sources.extend(out.get("sources_used", []))

        # Run quality evaluation
        aggregate = self.quality_scorer.evaluate(content, sources=sources)

        # Track iteration
        current_iter = state.get("current_iteration", 0) + 1
        version = RefinementVersion(
            iteration=current_iter,
            content=content[:2000],
            critique=aggregate,
            token_usage=len(content.split()) * 2,
        )

        return {
            "critiques": aggregate.critiques,
            "aggregated_critique": aggregate,
            "current_iteration": current_iter,
            "refinement_history": state.get("refinement_history", []) + [version],
            "status": "critique_completed",
        }

    def refine_output(self, state: DecisionGraphState) -> Dict[str, Any]:
        """Node: Refine the decision based on critique feedback."""
        decision = state.get("decision")
        critique = state.get("aggregated_critique")

        if not decision or not critique:
            return {"status": "nothing_to_refine"}

        # Use the refinement loop for a single improvement pass
        content = (
            f"Decision: {decision.decision}\n"
            f"Confidence: {decision.confidence}\n"
            f"Reasons: {json.dumps(decision.reasons)}\n"
            f"Risks: {json.dumps(decision.risks)}"
        )

        loop = IterativeRefinementLoop(llm=self.llm, config=RefinementConfig(max_iterations=1))
        result = loop.run(content, critique_fn=lambda _: critique)

        # Re-generate decision with improved context
        improved_decision = self.decision_maker.decide(
            query=state["query"],
            agent_outputs=state.get("agent_outputs", []),
            domain=state.get("domain", "general"),
            constraints=[f"Address these issues: {', '.join(i for c in critique.critiques for i in c.issues)}"],
        )

        return {"decision": improved_decision, "status": "refined"}

    def extract_kpis(self, state: DecisionGraphState) -> Dict[str, Any]:
        """Node: Extract KPIs from agent outputs."""
        agent_outputs = state.get("agent_outputs", [])
        query = state["query"]
        domain = state.get("domain", "general")

        # Combine all agent outputs
        combined_content = "\n\n".join(out.get("output", "") for out in agent_outputs)

        # Extract entity name from query (simplified)
        entity = query.split("analyze")[-1].strip() if "analyze" in query.lower() else query[:50]

        kpi_report = self.kpi_extractor.extract(
            content=combined_content,
            entity=entity,
            domain=domain,
        )

        return {"kpis": kpi_report, "status": "kpis_extracted"}

    def score_sources(self, state: DecisionGraphState) -> Dict[str, Any]:
        """Node: Score source reliability."""
        agent_outputs = state.get("agent_outputs", [])

        all_sources = []
        for out in agent_outputs:
            all_sources.extend(out.get("sources_used", []))

        # Deduplicate
        unique_sources = list(dict.fromkeys(all_sources))

        scored = self.source_scorer.score_sources(unique_sources)

        return {"sources": scored, "status": "sources_scored"}

    def format_report(self, state: DecisionGraphState) -> Dict[str, Any]:
        """Node: Generate the final enterprise report."""
        decision = state.get("decision")
        agent_outputs = state.get("agent_outputs", [])
        kpis = state.get("kpis")
        sources = state.get("sources", [])

        # Build executive summary from agent outputs
        summaries = []
        for out in agent_outputs:
            output_text = out.get("output", "")
            if output_text:
                summaries.append(output_text[:500])
        exec_summary = " ".join(summaries)[:1500] if summaries else "Analysis complete."

        # Extract insights, risks, recommendations from decision
        key_insights = decision.reasons if decision else ["Analysis completed"]
        risks = decision.risks if decision else []
        recommendations = []
        if decision:
            recommendations.append(f"{decision.decision} (Confidence: {decision.confidence:.0%})")
            recommendations.extend(decision.alternatives)

        report = EnterpriseReport(
            executive_summary=exec_summary,
            key_insights=key_insights,
            risks=risks,
            recommendations=recommendations,
            kpis=kpis,
            sources=sources,
            decision=decision,
        )

        # Generate formatted outputs
        title = f"Decision Analysis: {state['query'][:80]}"
        markdown = self.report_formatter.to_markdown(report, title=title)

        # Save files
        md_path = self.report_formatter.save_markdown(markdown)
        pdf_path = ""
        try:
            pdf_path = self.report_formatter.to_pdf(report, title=title)
        except Exception as e:
            log.warning("PDF generation failed", error=str(e))

        # Store outcome in long-term memory
        try:
            self.long_term.store_query_outcome(
                query=state["query"],
                decision=decision.decision if decision else "No decision",
                success=True,
            )
        except Exception:
            pass

        return {
            "enterprise_report": report,
            "final_output": markdown,
            "status": "completed",
        }

    # ─────────────────────────────────────────
    # Conditional Routing
    # ─────────────────────────────────────────

    def should_refine(self, state: DecisionGraphState) -> str:
        """Conditional edge: decide whether to refine or proceed to finalization."""
        critique = state.get("aggregated_critique")
        iteration = state.get("current_iteration", 0)
        max_iter = state.get("max_iterations", 3)

        if not critique:
            return "finalize"

        # Refine if score below threshold and iterations remaining
        if critique.revision_needed and iteration < max_iter:
            log.info("Routing to refinement", score=critique.overall_score, iteration=iteration)
            return "refine"

        log.info("Routing to finalization", score=critique.overall_score)
        return "finalize"

    # ─────────────────────────────────────────
    # Graph Construction
    # ─────────────────────────────────────────

    def build(self) -> StateGraph:
        """Build the complete decision workflow graph."""
        graph = StateGraph(DecisionGraphState)

        # Add nodes
        graph.add_node("decompose_task", self.decompose_task)
        graph.add_node("dispatch_agents", self.dispatch_agents)
        graph.add_node("generate_decision", self.generate_decision)
        graph.add_node("critique_output", self.critique_output)
        graph.add_node("refine_output", self.refine_output)
        graph.add_node("extract_kpis", self.extract_kpis)
        graph.add_node("score_sources", self.score_sources)
        graph.add_node("format_report", self.format_report)

        # Define edges
        graph.set_entry_point("decompose_task")
        graph.add_edge("decompose_task", "dispatch_agents")
        graph.add_edge("dispatch_agents", "generate_decision")
        graph.add_edge("generate_decision", "critique_output")

        # Conditional: refine or finalize
        graph.add_conditional_edges(
            "critique_output",
            self.should_refine,
            {
                "refine": "refine_output",
                "finalize": "extract_kpis",
            },
        )

        # Refine loops back to critique
        graph.add_edge("refine_output", "critique_output")

        # Finalization pipeline
        graph.add_edge("extract_kpis", "score_sources")
        graph.add_edge("score_sources", "format_report")
        graph.add_edge("format_report", END)

        self._graph = graph.compile(checkpointer=self.memory_saver)
        log.info("Decision workflow graph compiled")
        return self._graph

    # Step-to-progress mapping (approximate percentages)
    STEP_PROGRESS = {
        "decompose_task": 10.0,
        "dispatch_agents": 45.0,
        "generate_decision": 60.0,
        "critique_output": 70.0,
        "refine_output": 75.0,
        "extract_kpis": 80.0,
        "score_sources": 90.0,
        "format_report": 100.0,
    }

    def run(
        self,
        query: str,
        domain: str = "general",
        max_iterations: int = 3,
        thread_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full decision workflow.

        Args:
            query: User's analysis query.
            domain: Domain context (finance, healthcare, general).
            max_iterations: Max refinement iterations.
            thread_id: Optional thread ID for state persistence.
            task_id: Optional task ID for progress broadcasting.

        Returns:
            Dict with final_output, enterprise_report, decision, status.
        """
        if not self._graph:
            self.build()

        thread_id = thread_id or f"decision_{int(time.time())}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "query": query,
            "domain": domain,
            "max_iterations": max_iterations,
            "wf_task_id": task_id or "",
            "task_plan": None,
            "agent_outputs": [],
            "short_term_memory": {},
            "long_term_context": [],
            "decision": None,
            "critiques": [],
            "aggregated_critique": None,
            "refinement_history": [],
            "current_iteration": 0,
            "sources": [],
            "kpis": None,
            "enterprise_report": None,
            "final_output": "",
            "status": "started",
        }

        log.info("Starting decision workflow", query=query[:100], domain=domain, thread_id=thread_id)

        if task_id:
            broadcast_progress(task_id, "starting", 0.0, "running")

        # Stream through the graph
        final_state = None
        for step in self._graph.stream(initial_state, config):
            node_name = list(step.keys())[0]
            log.info("Workflow step completed", node=node_name)
            final_state = step[node_name]

            # Update task queue state + broadcast via WebSocket
            if task_id:
                pct = self.STEP_PROGRESS.get(node_name, 0.0)
                try:
                    from research_and_analyst.api.routes.api_routes import _get_task_queue
                    queue = _get_task_queue()
                    queue.checkpoint(task_id, node_name)
                except Exception:
                    pass
                broadcast_progress(task_id, node_name, pct, "running")

        return {
            "thread_id": thread_id,
            "final_output": final_state.get("final_output", "") if final_state else "",
            "status": final_state.get("status", "unknown") if final_state else "failed",
            "decision": final_state.get("decision") if final_state else None,
        }
