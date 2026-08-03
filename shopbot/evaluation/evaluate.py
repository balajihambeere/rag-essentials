# evaluation/evaluate.py
# Source: Book 1, Chapter 9 (Appendix A — Code Wiring)
# Runs all 20 test cases through the live retrieval and generation pipeline,
# then evaluates with RAGAS Faithfulness and Context Precision.
# Book 1 baseline: Faithfulness 0.71 | Context Precision 0.82
#
# Logs per-query: question, retrieved chunks, similarity scores, chunk types,
# embed tokens, LLM input/output tokens, per-query costs, ragas scores.
# Results saved to evaluation/results/<run_id>.json after every run.
# Cost estimate pre-logged in costs/cost_log.md before running.

try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, context_precision
    import ragas.executor as _rex
    from tqdm.auto import tqdm as _tqdm_auto

    # Python 3.12+ compatibility fix for ragas 0.1.22.
    # Root cause: _AsCompletedIterator.__init__ calls ensure_future(aw, loop=loop)
    # BEFORE asyncio.run() — so tasks land on loop A while asyncio.run() creates
    # loop B. Tasks on loop A never execute; the done-queue never fills; hang.
    # Fix: move as_completed() INSIDE asyncio.run() so ensure_future() targets
    # the running loop B.
    def _patched_executor_results(self):
        import asyncio
        if _rex.is_event_loop_running():
            try:
                import nest_asyncio
            except ImportError:
                raise ImportError("pip install nest_asyncio")
            if not self._nest_asyncio_applied:
                nest_asyncio.apply()
                self._nest_asyncio_applied = True

        coros = [f(*a, **kw) for f, a, kw, _ in self.jobs]
        max_workers = (self.run_config or _rex.RunConfig()).max_workers

        async def _run():
            # inside run() → right loop
            futs = _rex.as_completed(coros, max_workers)
            results = []
            for fut_coro in _tqdm_auto(futs, desc=self.desc, total=len(self.jobs),
                                       leave=self.keep_progress_bar):
                results.append(await fut_coro)
            return results

        raw = asyncio.run(_run())
        return [r[1] for r in sorted(raw, key=lambda x: x[0])]

    _rex.Executor.results = _patched_executor_results
    RAGAS_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    RAGAS_AVAILABLE = False
    _ragas_error = e

import json
import os
import time
import tiktoken
from datetime import datetime
from datasets import Dataset
from dotenv import load_dotenv
from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import SystemMessage, HumanMessage

from evaluation.test_cases import TEST_CASES
from src.retriever import retrieve
from src.prompt import llm, SHOPBOT_SYSTEM

load_dotenv()

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

# Pricing — gpt-4o-mini + text-embedding-3-small (per 1M tokens)
EMBED_PRICE_PER_M = 0.02
LLM_INPUT_PRICE_PER_M = 0.15
LLM_OUTPUT_PRICE_PER_M = 0.60

_enc = tiktoken.get_encoding("cl100k_base")


def _count(text: str) -> int:
    return len(_enc.encode(text))


def _cost(tokens: int, price_per_m: float) -> float:
    return tokens / 1_000_000 * price_per_m


def run_single_query(case: dict) -> dict:
    """
    Run one test case through the full pipeline. Returns a per-query log dict
    with every measurable value captured at the point it occurs.
    Single retrieve() call — result is reused for both ragas dataset and logging.
    """
    query = case["query"]

    # ── 1. Embedding (query → vector) ────────────────────────────────────────
    embed_tokens = _count(query)
    embed_cost = _cost(embed_tokens, EMBED_PRICE_PER_M)

    # ── 2. Retrieval ─────────────────────────────────────────────────────────
    evidence = retrieve(query)
    retrieval_succeeded = evidence is not None

    chunks_log = []
    if evidence:
        for e in evidence:
            chunks_log.append({
                "chunk_id":   e["metadata"].get("product_id", "") + "_" + e["metadata"].get("chunk_type", ""),
                "product_id": e["metadata"].get("product_id", ""),
                "chunk_type": e["metadata"].get("chunk_type", ""),
                "similarity": e["similarity"],
                "tokens":     _count(e["text"]),
                "text":       e["text"],
            })

    # ── 3. Context string ────────────────────────────────────────────────────
    if evidence:
        context = "\n\n---\n\n".join(
            f"[{e['metadata']['chunk_type'].upper()}]\n{e['text']}"
            for e in evidence
        )
        ragas_contexts = [e["text"] for e in evidence]
    else:
        context = ""
        ragas_contexts = [""]

    context_tokens = _count(context)

    # ── 4. LLM generation (with token tracking) ──────────────────────────────
    messages = [
        SystemMessage(content=SHOPBOT_SYSTEM.format(context=context)),
        HumanMessage(content=query),
    ]
    prompt_tokens = sum(_count(m.content) for m in messages)

    if not retrieval_succeeded:
        answer = (
            "I don't have a product that matches that specifically. "
            "Could you describe what you're looking for differently, "
            "or contact our team at support@zudyog.com?"
        )
        llm_input_tokens = 0
        llm_output_tokens = 0
    else:
        with get_openai_callback() as cb:
            response = llm.invoke(messages)
        answer = response.content
        llm_input_tokens = cb.prompt_tokens
        llm_output_tokens = cb.completion_tokens

    answer_tokens = _count(answer)
    llm_input_cost = _cost(llm_input_tokens,  LLM_INPUT_PRICE_PER_M)
    llm_output_cost = _cost(llm_output_tokens, LLM_OUTPUT_PRICE_PER_M)
    query_total_cost = embed_cost + llm_input_cost + llm_output_cost

    return {
        # ── ragas dataset row ─────────────────────────────────────────────
        "_ragas_row": {
            "question":     query,
            "answer":       answer,
            "contexts":     ragas_contexts,
            "ground_truth": case["expected_answer"],
        },
        # ── full per-query log ────────────────────────────────────────────
        "question":            query,
        "expected_answer":     case["expected_answer"],
        "answer":              answer,
        "retrieval_succeeded": retrieval_succeeded,
        "chunks_retrieved":    len(chunks_log),
        "chunks":              chunks_log,
        "tokens": {
            "embed_query":   embed_tokens,
            "context":       context_tokens,
            "prompt_total":  prompt_tokens,
            "llm_input":     llm_input_tokens,
            "llm_output":    llm_output_tokens,
            "answer":        answer_tokens,
        },
        "cost_usd": {
            "embed":      round(embed_cost,      8),
            "llm_input":  round(llm_input_cost,  8),
            "llm_output": round(llm_output_cost, 8),
            "total":      round(query_total_cost, 8),
        },
        # ragas per-query scores filled in after evaluate() completes
        "ragas": {
            "faithfulness":      None,
            "context_precision": None,
        },
    }


def save_results(run_id: str, query_logs: list, overall: dict, elapsed: float) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{run_id}.json")

    # Aggregate cost totals
    total_embed_tokens = sum(q["tokens"]["embed_query"] for q in query_logs)
    total_llm_input = sum(q["tokens"]["llm_input"] for q in query_logs)
    total_llm_output = sum(q["tokens"]["llm_output"] for q in query_logs)
    total_context_tokens = sum(q["tokens"]["context"] for q in query_logs)
    total_answer_tokens = sum(q["tokens"]["answer"] for q in query_logs)
    total_embed_cost = sum(q["cost_usd"]["embed"] for q in query_logs)
    total_llm_cost = sum(q["cost_usd"]["llm_input"] +
                         q["cost_usd"]["llm_output"] for q in query_logs)
    total_cost = sum(q["cost_usd"]["total"] for q in query_logs)
    retrieved_count = sum(1 for q in query_logs if q["retrieval_succeeded"])

    output = {
        "run_id":        run_id,
        "timestamp":     datetime.utcnow().isoformat() + "Z",
        "ragas_version": "0.1.22",
        "model_embed":   "text-embedding-3-small",
        "model_llm":     "gpt-4o-mini",
        "run_time_sec":  round(elapsed, 2),
        "summary": {
            "total_queries":        len(query_logs),
            "queries_retrieved":    retrieved_count,
            "queries_fallback":     len(query_logs) - retrieved_count,
            "faithfulness":         overall["faithfulness"],
            "context_precision":    overall["context_precision"],
            "book1_baseline": {
                "faithfulness":      0.71,
                "context_precision": 0.82,
            },
            "tokens": {
                "embed_total":        total_embed_tokens,
                "context_total":      total_context_tokens,
                "llm_input_total":    total_llm_input,
                "llm_output_total":   total_llm_output,
                "answer_total":       total_answer_tokens,
            },
            "cost_usd": {
                "embed":      round(total_embed_cost, 6),
                "llm":        round(total_llm_cost,   6),
                "total":      round(total_cost,        6),
            },
        },
        "queries": query_logs,
    }

    with open(path, "w") as f:
        json.dump(output, f, indent=2)

    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-checkpoint", metavar="FILE",
                        help="Skip Step 1: load pipeline results from a checkpoint JSON and run only RAGAS scoring.")
    args = parser.parse_args()

    if not RAGAS_AVAILABLE:
        print(f"ERROR: ragas not importable — {_ragas_error}")
        print("Fix: pip install 'ragas==0.1.22'")
        raise SystemExit(1)

    run_id = "run_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    t_start = time.time()

    print(f"Run: {run_id}")
    print(f"Queries: {len(TEST_CASES)}")
    print()

    # ── Step 1: pipeline (retrieve + generate) ───────────────────────────────
    if args.from_checkpoint:
        # Reload Step 1 results — zero API cost
        print(f"── Step 1/3: Loading checkpoint ({args.from_checkpoint}) ──")
        with open(args.from_checkpoint) as f:
            ckpt = json.load(f)
        query_logs = ckpt["queries"]
        # Re-add _ragas_row for RAGAS (strip was applied when saving)
        for q in query_logs:
            q["_ragas_row"] = {
                "question":     q["question"],
                "answer":       q["answer"],
                "contexts":     [c["text"] for c in q["chunks"]] if q["chunks"] else [""],
                "ground_truth": q["expected_answer"],
            }
        print(
            f"  Loaded {len(query_logs)} queries from checkpoint — skipping pipeline API calls.")
    else:
        print("── Step 1/3: Pipeline (retrieve + generate) ──")
        query_logs = []
        for i, case in enumerate(TEST_CASES, 1):
            log = run_single_query(case)
            query_logs.append(log)
            status = "✓" if log["retrieval_succeeded"] else "✗ (fallback)"
            print(f"  [{i:02d}/20] {status}  chunks={log['chunks_retrieved']}  "
                  f"tokens={log['tokens']['llm_input']}in/{log['tokens']['llm_output']}out  "
                  f"${log['cost_usd']['total']:.6f}")

        # Save checkpoint immediately after Step 1 — RAGAS can now be retried for free
        os.makedirs(RESULTS_DIR, exist_ok=True)
        ckpt_path = os.path.join(RESULTS_DIR, f"{run_id}_checkpoint.json")
        with open(ckpt_path, "w") as f:
            # Write without _ragas_row (internal only)
            saveable = [{k: v for k, v in q.items() if k != "_ragas_row"}
                        for q in query_logs]
            json.dump({"run_id": run_id, "queries": saveable}, f, indent=2)
        print(f"\n  Checkpoint saved → {ckpt_path}")
        print(
            f"  If RAGAS fails: python -m evaluation.evaluate --from-checkpoint {ckpt_path}")

    # ── Step 2: RAGAS evaluation ──────────────────────────────────────────────
    print()
    print("── Step 2/3: RAGAS scoring ──")
    ragas_dataset = Dataset.from_list([q["_ragas_row"] for q in query_logs])
    result = evaluate(ragas_dataset, metrics=[faithfulness, context_precision])

    # Attach per-query ragas scores
    for i, scores in enumerate(result.scores):
        query_logs[i]["ragas"]["faithfulness"] = round(
            scores.get("faithfulness",      0), 4)
        query_logs[i]["ragas"]["context_precision"] = round(
            scores.get("context_precision", 0), 4)

    # Remove internal ragas row from saved output
    for q in query_logs:
        del q["_ragas_row"]

    # ── Step 3: Save ─────────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    overall = {
        "faithfulness":      round(result["faithfulness"],      4),
        "context_precision": round(result["context_precision"], 4),
    }
    path = save_results(run_id, query_logs, overall, elapsed)

    # ── Print summary ─────────────────────────────────────────────────────────
    total_cost = sum(q["cost_usd"]["total"] for q in query_logs)
    total_in = sum(q["tokens"]["llm_input"] for q in query_logs)
    total_out = sum(q["tokens"]["llm_output"] for q in query_logs)

    print()
    print("── Step 3/3: Results ────────────────────────────────────────")
    print(
        f"  Faithfulness:       {overall['faithfulness']:.4f}  (book1 target 0.71)")
    print(
        f"  Context Precision:  {overall['context_precision']:.4f}  (book1 target 0.82)")
    print()
    print(
        f"  Queries retrieved:  {sum(1 for q in query_logs if q['retrieval_succeeded'])}/20")
    print(f"  LLM tokens:         {total_in} input / {total_out} output")
    print(f"  Total cost:         ${total_cost:.6f}")
    print(f"  Run time:           {elapsed:.1f}s")
    print()
    print(f"  Results → {path}")
    print("─────────────────────────────────────────────────────────────")

    # ── Optional: MLflow experiment tracking ─────────────────────────────────
    _mlflow_uri = os.getenv("MLFLOW_TRACKING_URI")
    if _mlflow_uri:
        try:
            import mlflow
            mlflow.set_tracking_uri(_mlflow_uri)
            mlflow.set_experiment("shopbot-eval")
            with mlflow.start_run(run_name=run_id):
                mlflow.log_params({
                    "model_embed":          "text-embedding-3-small",
                    "model_llm":            "gpt-4o-mini",
                    "ragas_version":        "0.1.22",
                    "similarity_threshold": 0.75,
                    "max_results":          3,
                    "total_queries":        len(query_logs),
                })
                mlflow.log_metrics({
                    "faithfulness":        overall["faithfulness"],
                    "context_precision":   overall["context_precision"],
                    "queries_retrieved":   sum(1 for q in query_logs if q["retrieval_succeeded"]),
                    "total_cost_usd":      round(total_cost, 6),
                    "run_time_sec":        round(elapsed, 2),
                    "llm_input_tokens":    total_in,
                    "llm_output_tokens":   total_out,
                })
            print(f"  MLflow  → {_mlflow_uri}  (experiment: shopbot-eval)")
        except Exception as _mlflow_err:
            print(f"  MLflow logging skipped: {_mlflow_err}")
