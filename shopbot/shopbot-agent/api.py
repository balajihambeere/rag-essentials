# shopbot-agent/api.py
# Source: Book 1, Chapter 8 (Appendix A — Code Wiring)
# FastAPI endpoint exposing ShopBot to the world.
# Two routes: GET /health for deployment probes, POST /ask for customer questions.
# Chain built once at startup via lifespan — never inside request handlers. (Ch. 8)
# Input validation rejects empty strings, questions over 500 chars,
# and common prompt-injection patterns before they reach the chain. (Ch. 8)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from contextlib import asynccontextmanager
import os
import re
import uvicorn

from chain import build_chain

# ── Lifespan: build the chain once at startup ─────────────────────────────────
shopbot_chain = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global shopbot_chain
    _mlflow_uri = os.getenv("MLFLOW_TRACKING_URI")
    if _mlflow_uri:
        try:
            import mlflow
            mlflow.set_tracking_uri(_mlflow_uri)
            mlflow.set_experiment("shopbot-eval")
            mlflow.langchain.autolog()
            print(f"  MLflow tracing → {_mlflow_uri}  (experiment: shopbot-eval)")
        except Exception as e:
            print(f"  MLflow tracing skipped: {e}")
    print("Building ShopBot chain...")
    shopbot_chain = build_chain()
    print("ShopBot ready.")
    yield
    # Shutdown: no cleanup needed for local ChromaDB


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ShopBot API",
    description="AI-powered product assistant for zUdyog Fashion",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Request and Response Models ───────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question:   str
    session_id: str = "default"  # carried through to response; chain itself is stateless

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()

        # Normalise common word-processor characters
        v = v.replace("‘", "'").replace("’", "'")   # smart single quotes
        v = v.replace("“", '"').replace("”", '"')   # smart double quotes
        v = v.replace("—", " - ")                        # em dash
        v = v.replace("​", "")                           # zero-width space

        if not v:
            raise ValueError("Question cannot be empty.")
        if len(v) > 500:
            raise ValueError(
                f"Question too long ({len(v)} characters). Maximum is 500."
            )

        # Five injection patterns from Ch. 8 — covers jailbreak attempts before
        # the question reaches the chain. Error message is intentionally vague.
        injection_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"you\s+are\s+now\s+",
            r"act\s+as\s+",
            r"system\s+prompt",
            r"forget\s+(everything|all)",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid question format.")

        return v


class AnswerResponse(BaseModel):
    answer:     str
    session_id: str


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    """Health check for Railway deployment probes and uptime monitoring."""
    return {"status": "ok", "service": "ShopBot", "version": "1.0.0"}


@app.post("/ask", response_model=AnswerResponse)
def ask_shopbot(payload: QuestionRequest):
    """
    Ask ShopBot a product question.
    Returns a grounded answer sourced from zUdyog Fashion's catalog,
    or a deliberate fallback routed to support@example.com.
    """
    answer = shopbot_chain.invoke(payload.question)
    return AnswerResponse(answer=answer, session_id=payload.session_id)


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8000
    print("ShopBot API starting...")
    print(f"  API:     http://localhost:{port}")
    print(f"  Swagger: http://localhost:{port}/docs")
    print(f"  Health:  http://localhost:{port}/health")
    uvicorn.run("api:app", host=host, port=port, reload=True)
