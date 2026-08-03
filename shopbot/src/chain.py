# src/chain.py
# Source: Book 1, Chapter 7 (Appendix A — Code Wiring)
# Wires retrieval, prompt, and LLM into a single LangChain expression language chain.
# build_chain() is called once at API startup and reused for every request.
# The chain is stateless — no session memory. Each invocation is independent.

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from src.retriever import get_retriever
from src.prompt import SHOPBOT_SYSTEM

load_dotenv()


def format_docs(docs: list) -> str:
    """Convert retrieved Documents into a numbered, labelled context string."""
    if not docs:
        return "No product information available."
    formatted = []
    for i, doc in enumerate(docs, 1):
        chunk_type = doc.metadata.get("chunk_type", "general")
        # Label each item by type so the LLM can distinguish care vs variants vs FAQ
        formatted.append(f"[Item {i} — {chunk_type}]\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


def build_chain():
    """Build the full RAG chain. Called once at startup; reused for every request."""
    retriever = get_retriever(k=3)
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,  # Deterministic — same input must always produce same output (Ch. 7)
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SHOPBOT_SYSTEM),
        ("human", "{question}"),
    ])
    chain = (
        {
            "context":  retriever | format_docs,  # retrieve → format into labelled string
            "question": RunnablePassthrough(),     # pass question through unchanged
        }
        | prompt   # inject context + question into ChatPromptTemplate
        | llm      # gpt-4o-mini at temperature=0
        | StrOutputParser()  # extract .content from AIMessage → plain string
    )
    return chain
