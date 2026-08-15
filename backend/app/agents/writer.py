"""Writer agent — drafts the final research report from gathered research."""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.app.agents.llm import get_llm

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

The research above includes an EVIDENCE section, a CLAIMS section, a FACT
CHECKS section, and a CITATIONS section.

Rules:
- In Key Findings, cite each source with its numbered citation from the
  CITATIONS section, e.g. [1], [2]. Never use evidence IDs like [E1] as
  citations.
- End with a "Sources" section listing every citation as "[n] Title — URL".
- Use ONLY facts present in the research. Do not invent sources.

Structure the report as:
- Introduction
- Key Findings (minimum 4 well-explained points, each citing sources)
- Conclusion
- Sources

Be detailed, factual and professional."""),
])

writer_chain = writer_prompt | get_llm() | StrOutputParser()
