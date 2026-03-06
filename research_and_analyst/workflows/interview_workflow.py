"""
Interview Sub-Graph for the Autonomous Research Report Generator.

Builds a LangGraph sub-graph that loops through:
  ask_question → search_web → answer_question → (repeat or save) → write_section
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, get_buffer_string
from langgraph.graph import StateGraph, END

from research_and_analyst.schemas import InterviewState
from research_and_analyst.prompt_library import (
    INTERVIEW_QUESTION_PROMPT,
    SEARCH_QUERY_PROMPT,
    ANSWER_PROMPT,
    SECTION_WRITER_PROMPT,
)
from research_and_analyst.logger import GLOBAL_LOGGER as log
from research_and_analyst.exception.custom_exception import ResearchAnalystException


class InterviewGraphBuilder:
    """
    Constructs a compiled LangGraph sub-graph that conducts a single
    multi-turn interview between an analyst persona and an expert,
    using web search for grounding.
    """

    def __init__(self, llm, tavily_search):
        self.llm = llm
        self.tavily_search = tavily_search

    # ─── Node: analyst asks a question ────────────────────────────────
    def ask_question(self, state: InterviewState):
        try:
            analyst = state["analyst"]
            messages = state.get("messages", [])

            topic = ""
            if messages:
                topic = messages[0].content

            prompt = INTERVIEW_QUESTION_PROMPT.format(
                topic=topic,
                persona=analyst.persona,
            )

            system_msg = [HumanMessage(content=prompt)] + messages

            response = self.llm.invoke(system_msg)

            log.info(
                "Analyst question generated",
                analyst=analyst.name,
                question=response.content[:120],
            )

            return {"messages": [response]}

        except Exception as e:
            log.error("Error generating analyst question", error=str(e))
            raise ResearchAnalystException("Failed to generate analyst question", e)

    # ─── Node: run web search ─────────────────────────────────────────
    def search_web(self, state: InterviewState):
        try:
            messages = state.get("messages", [])
            last_message = messages[-1] if messages else None

            if not last_message:
                return {"context": []}

            question = last_message.content

            # Generate search queries
            query_prompt = SEARCH_QUERY_PROMPT.format(
                question=question,
                num_queries=3,
            )
            query_response = self.llm.invoke([HumanMessage(content=query_prompt)])

            # Parse queries (one per line)
            raw_queries = query_response.content.strip().split("\n")
            queries = []
            for q in raw_queries:
                cleaned = q.strip().lstrip("0123456789.-) ").strip()
                if cleaned:
                    queries.append(cleaned)

            if not queries:
                queries = [question]

            # Execute searches
            search_results = []
            for query in queries[:3]:
                try:
                    results = self.tavily_search.invoke({"query": query})
                    if isinstance(results, list):
                        for r in results[:2]:
                            content = r.get("content", "") if isinstance(r, dict) else str(r)
                            if content:
                                search_results.append(content)
                    elif isinstance(results, str):
                        search_results.append(results)
                except Exception as search_err:
                    log.warning("Search query failed", query=query, error=str(search_err))

            log.info("Web search completed", num_results=len(search_results))
            return {"context": search_results}

        except Exception as e:
            log.error("Error during web search", error=str(e))
            raise ResearchAnalystException("Failed to search web", e)

    # ─── Node: expert answers using context ───────────────────────────
    def answer_question(self, state: InterviewState):
        try:
            messages = state.get("messages", [])
            context = state.get("context", [])
            max_turns = state.get("max_num_turns", 2)

            # Count the number of AI responses so far (each represents a turn)
            num_turns = sum(1 for m in messages if isinstance(m, AIMessage))

            last_question = ""
            if messages:
                last_question = messages[-1].content

            context_str = "\n\n---\n\n".join(context) if context else "No context available."

            prompt = ANSWER_PROMPT.format(
                question=last_question,
                context=context_str,
            )

            response = self.llm.invoke([HumanMessage(content=prompt)])

            log.info("Expert answer generated", turns_completed=num_turns + 1)

            result_messages = [response]

            # If we've reached max turns, signal completion
            if num_turns + 1 >= max_turns:
                result_messages.append(
                    ToolMessage(
                        content="answer_expert",
                        tool_call_id="interview_done",
                        name="interview_signal",
                    )
                )
                log.info("Max interview turns reached, signalling completion")

            return {"messages": result_messages}

        except Exception as e:
            log.error("Error generating expert answer", error=str(e))
            raise ResearchAnalystException("Failed to generate expert answer", e)

    # ─── Conditional: route after answer ──────────────────────────────
    @staticmethod
    def route_messages(state: InterviewState):
        messages = state.get("messages", [])

        # Check if the last message is our completion signal
        if messages and isinstance(messages[-1], ToolMessage):
            if messages[-1].content == "answer_expert":
                return "save_interview"

        return "ask_question"

    # ─── Node: persist the full interview transcript ──────────────────
    def save_interview(self, state: InterviewState):
        try:
            messages = state.get("messages", [])
            # Filter out the signal ToolMessage
            conv_messages = [m for m in messages if not isinstance(m, ToolMessage)]
            interview_text = get_buffer_string(conv_messages)
            log.info("Interview saved", length=len(interview_text))
            return {"interview": interview_text}

        except Exception as e:
            log.error("Error saving interview", error=str(e))
            raise ResearchAnalystException("Failed to save interview", e)

    # ─── Node: write a report section from the interview ──────────────
    def write_section(self, state: InterviewState):
        try:
            interview = state.get("interview", "")
            analyst = state["analyst"]

            prompt = SECTION_WRITER_PROMPT.format(interview=interview)
            response = self.llm.invoke([HumanMessage(content=prompt)])

            log.info("Section written", analyst=analyst.name)
            return {"sections": [response.content]}

        except Exception as e:
            log.error("Error writing section", error=str(e))
            raise ResearchAnalystException("Failed to write section", e)

    # ─── Build & compile the sub-graph ────────────────────────────────
    def build(self):
        try:
            log.info("Building interview sub-graph")

            builder = StateGraph(InterviewState)

            builder.add_node("ask_question", self.ask_question)
            builder.add_node("search_web", self.search_web)
            builder.add_node("answer_question", self.answer_question)
            builder.add_node("save_interview", self.save_interview)
            builder.add_node("write_section", self.write_section)

            # Entry → ask_question
            builder.set_entry_point("ask_question")

            # ask → search → answer
            builder.add_edge("ask_question", "search_web")
            builder.add_edge("search_web", "answer_question")

            # answer → conditional (loop or save)
            builder.add_conditional_edges(
                "answer_question",
                self.route_messages,
                {
                    "ask_question": "ask_question",
                    "save_interview": "save_interview",
                },
            )

            # save → write_section → END
            builder.add_edge("save_interview", "write_section")
            builder.add_edge("write_section", END)

            graph = builder.compile()
            log.info("Interview sub-graph built successfully")
            return graph

        except Exception as e:
            log.error("Error building interview sub-graph", error=str(e))
            raise ResearchAnalystException("Failed to build interview sub-graph", e)
