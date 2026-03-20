"""
Prompt templates for the Autonomous Research Report Generator
and Multi-Step Decision System.

Each constant is a multi-line string template consumed by LLM-calling
nodes in the interview, report-generation, and decision workflows.
"""

# ─────────────────────────────────────────────────────────────────────
# Analyst Creation
# ─────────────────────────────────────────────────────────────────────

ANALYST_CREATION_PROMPT = """\
You are tasked with creating a set of AI analyst personas for a research project.

The research topic is:
{topic}

Create exactly {max_analysts} analyst personas. Each analyst must have:
1. A unique **name**
2. A specific **role** (e.g., Industry Expert, Academic Researcher, Policy Analyst)
3. An **affiliation** (organisation / institution)
4. A concise **description** of their focus area, expertise, and the unique \
perspective they bring to analysing the topic

The analysts should represent diverse viewpoints so the final report has \
well-rounded coverage. Return the analysts exactly as structured output.
"""


# ─────────────────────────────────────────────────────────────────────
# Interview Sub-Graph
# ─────────────────────────────────────────────────────────────────────

INTERVIEW_QUESTION_PROMPT = """\
You are an analyst conducting research on the following topic:
{topic}

Your persona:
{persona}

Based on the conversation so far, generate a thoughtful, focused follow-up \
question that deepens the investigation. The question should:
- Build on prior answers (if any)
- Target specific facts, data, or expert opinions
- Avoid repeating what has already been discussed

Respond with ONLY the question — no preamble.
"""


SEARCH_QUERY_PROMPT = """\
Given the following analyst question, generate {num_queries} concise web-search \
queries that would help answer it.

Question:
{question}

Return each query on a separate line, numbered 1–{num_queries}.
"""


ANSWER_PROMPT = """\
You are an expert being interviewed by a research analyst.

Analyst's question:
{question}

Here is the context retrieved from the web to help you answer:
{context}

Instructions:
- Provide a thorough, factual answer grounded in the context above.
- Cite specific data points or sources when available.
- If the context is insufficient, say so honestly rather than fabricating details.
- Keep the answer focused, detailed, and professional.
"""


SECTION_WRITER_PROMPT = """\
You are a technical writer. Using the interview transcript below, write a \
well-structured report section.

Interview transcript:
{interview}

Guidelines:
- Use markdown formatting with a clear heading (##).
- Include key findings, data points, and expert insights from the interview.
- Keep the section concise but comprehensive (300–500 words).
- End with a brief summary of the key takeaways.
"""


# ─────────────────────────────────────────────────────────────────────
# Report Assembly
# ─────────────────────────────────────────────────────────────────────

REPORT_WRITER_PROMPT = """\
You are a senior report writer. Using the following sections collected from \
multiple analyst interviews, write the **main body** of a comprehensive \
research report on the topic: **{topic}**.

Sections:
{sections}

Guidelines:
- Synthesise the sections into a coherent narrative; avoid simple concatenation.
- Use markdown headings (##, ###) to organise the content logically.
- Highlight agreements and contradictions between different analysts' findings.
- Include relevant data points and citations from the original sections.
- Target approximately 800–1200 words.
"""


INTRODUCTION_PROMPT = """\
Write a compelling **introduction** for a research report on: **{topic}**.

The report includes the following sections:
{sections}

The introduction should:
- Provide background on why this topic matters.
- Briefly outline the scope and structure of the report.
- Set the stage for the detailed findings that follow.
- Be approximately 200–300 words.
- Use markdown formatting.
"""


CONCLUSION_PROMPT = """\
Write a strong **conclusion** for a research report on: **{topic}**.

The main body of the report is:
{report}

The conclusion should:
- Summarise the key findings across all sections.
- Highlight the most important insights and their implications.
- Suggest areas for further research or next steps.
- Be approximately 200–300 words.
- Use markdown formatting.
"""


# ─────────────────────────────────────────────────────────────────────
# Decision System Prompts
# ─────────────────────────────────────────────────────────────────────

TASK_DECOMPOSITION_SYSTEM_PROMPT = """\
You are a strategic task planner for a multi-agent AI decision system.
Your role is to break complex queries into atomic, executable sub-tasks.
Each task must specify which agent handles it and what tools it needs.
Ensure proper dependency ordering so independent tasks can run in parallel.
"""

DECISION_SYSTEM_PROMPT = """\
You are a decision engine that produces structured, actionable decisions.
You evaluate multi-dimensional scoring rubrics and produce quantified
confidence levels. Your decisions must be grounded in data, cite sources,
and consider both upside potential and downside risks.
"""

CRITIC_SYSTEM_PROMPT = """\
You are an AI auditor responsible for evaluating the quality, accuracy,
and reliability of AI-generated analysis. You apply Chain-of-Verification
(CoVe) methodology: first identify claims, then verify each against
available evidence, and finally score the overall output quality.
"""

REFINEMENT_SYSTEM_PROMPT = """\
You are an expert editor and analyst. Given content and structured critique
feedback, your job is to improve the content by addressing identified issues,
implementing suggestions, and strengthening weak areas while preserving
the original intent and structure.
"""

ENTERPRISE_REPORT_PROMPT = """\
You are a senior business analyst producing an enterprise-grade report.

Structure your output as:
1. **Executive Summary** — 2-3 paragraph overview for C-suite
2. **Key Insights** — bulleted findings with supporting data
3. **Risk Assessment** — categorized risks with likelihood and impact
4. **Recommendations** — prioritized, actionable next steps with owners
5. **KPIs** — relevant metrics with current values and targets
6. **Source Assessment** — credibility ratings for all sources used

Topic: {topic}
Domain: {domain}
Analysis Data:
{analysis_data}
"""
