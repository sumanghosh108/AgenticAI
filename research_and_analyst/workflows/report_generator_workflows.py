from research_and_analyst.logger.custom_logger import CustomLogger



class AutonomousReportGenerator:
    def build_graph(self):
        
        try:
            self.logger.info("Building report generation graph")
            builder=StateGraph(ResearchGraphState)
            interview_graph=InterviewGraphBuilder(self.llm, selg.tavily_search).buuld()
            
            def initiate_all_interviews(state: ResearchGraphState):
                topic = state.get("topic", "Untitled Topic")
                analysts = state.get("analysts", [])

                if not analysts:
                    self.logger.warning("No analysts found — skipping interviews")
                    return END

                return [
                    Send(
                        "conduct_interview",
                        {
                            "analyst": analyst,
                            "messages": [
                                HumanMessage(content=f"So, let's discuss about {topic}.")
                            ],
                            "max_num_turns": 2,
                            "context": [],
                            "interview": "",
                            "sections": [],
                        },
                    )
                    for analyst in analysts
                ]
                
            builder.add_node("create_analyst", self.create_analyst)
            builder.add_node("human_feedback", self.human_feedback)
            builder.add_node("conduct_interview", interview_graph)
            builder.add_node("write_report", self.write_report)
            builder.add_node("write_introduction", self.write_introduction)
            builder.add_node("write_conclusion", self.write_conclusion)
            builder.add_node("finalize_report", self.finalize_report)

            builder.add_edge(START, "create_analyst")
            builder.add_edge("create_analyst", "human_feedback")

            builder.add_conditional_edges(
                "human_feedback",
                initiate_all_interviews,
                ["conduct_interview", END]
            )

            builder.add_edge("conduct_interview", "write_report")
            builder.add_edge("conduct_interview", "write_introduction")
            builder.add_edge("conduct_interview", "write_conclusion")

            builder.add_edge(
                ["write_report", "write_introduction", "write_conclusion"],
                "finalize_report"
            )

            builder.add_edge("finalize_report", END)


            graph = builder.compile(
                interrupt_before=["human_feedback"],
                checkpointer=self.memory
            )

            self.logger.info("Report generation graph built successfully")
            return graph
        except Exception as e:
            self.logger.error("Ettot building report graph", error=str(e))
            raise ReaearchAnalystException("Failed to build report geneartion graph", e)



# -------------------------------------
