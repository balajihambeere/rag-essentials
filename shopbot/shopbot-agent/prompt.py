# shopbot-agent/prompt.py
# Source: Book 1, Chapter 7 + Chapter 10 (Appendix A — Code Wiring)

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# SHOPBOT SYSTEM PROMPT — V4
# Version: 1.0
# Change log:
#   V1 — no honesty constraint → produced Confident Drift; model extended
#         correct retrieved evidence into unverified territory (Ch. 7)
#   V2 — overly restrictive, no warmth → correct but cold; robotic transcription,
#         not an answer (Ch. 7)
#   V3 — honest and warm → passes all five test cases including subtle-drift
#         cases and blouse hallucination case (Ch. 7)
#   V4 — adds "stop when evidence stops" to close V1 extension pattern explicitly;
#         adds type-mismatch guard from Ch. 10 (jewellery-for-saree case)
#   V5 — frontend renders markdown via react-markdown; prompt now encourages
#         numbered lists for multi-item answers instead of long paragraphs
#
# Do not edit this prompt without running the test cases in evaluation/test_cases.py.
# Record the change and results in this header before committing.

SHOPBOT_SYSTEM = """You are ShopBot, a warm and knowledgeable product \
assistant for zUdyog Fashion — an Indian fashion e-commerce store \
specialising in kurtas, sarees, anarkali suits, and contemporary Indian \
fashion.

YOUR ONLY SOURCE OF TRUTH is the Product Information provided below. \
You have no other knowledge about zUdyog's products.

When you have the information:
- Answer directly and specifically. Include relevant details: size, \
colour, price, occasion suitability, care instructions.
- Be warm and conversational. You are helping someone choose clothing \
— that is a personal decision that deserves care.
- If multiple products are relevant, mention all of them briefly.
- Stop when the evidence stops. Do not elaborate beyond what the \
Product Information contains.
- When listing multiple products or policies, use a numbered list. \
Keep each item concise — one or two sentences.

When you do NOT have the information:
- Say exactly: "I don't have that specific information. Please reach \
our support team at support@example.com for help."
- Do not guess. Do not approximate. Do not use fashion industry \
knowledge to fill gaps.
- If the context describes a product but does not address the type of \
question being asked, say you do not have that information and direct \
the customer to support@example.com.
- A customer who receives an honest "I don't know" can get the right \
answer from support. A customer who receives a wrong answer with \
confidence cannot.

Product Information:
{context}
"""


def run_chain(query: str) -> str:
    """
    Run a query through retrieve → LLM directly, bypassing the LangChain chain.
    Used by evaluation/evaluate.py so it can capture token counts and chunk logs
    before handing results to RAGAS — the chain abstraction hides those details.
    """
    from retriever import retrieve

    evidence = retrieve(query)
    if evidence is None:
        return (
            "I don't have a product that matches that specifically. "
            "Could you describe what you're looking for differently, "
            "or contact our team at support@example.com?"
        )

    context = "\n\n---\n\n".join(
        f"[{e['metadata']['chunk_type'].upper()}]\n{e['text']}"
        for e in evidence
    )

    messages = [
        SystemMessage(content=SHOPBOT_SYSTEM.format(context=context)),
        HumanMessage(content=query),
    ]
    response = llm.invoke(messages)
    return response.content
