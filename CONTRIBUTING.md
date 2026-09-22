# Contributing to RAG Essentials

Thanks for considering a contribution. This repo is the real, working codebase behind Book 1 of the RAG Mastery Series — it's meant to stay a runnable, honest reference implementation, not a polished framework. Contributions that keep it that way are the most welcome kind.

## Ground rules

- **Keep it runnable.** Every change should leave `python -m src.api` and `npm run dev` working from a clean clone, following `shopbot/README.md`.
- **Keep it honest.** This codebase intentionally shows Book 1's *un-optimized* architecture (single ChromaDB threshold, no re-ranking, no hybrid search) — that gap is what Book 2 exists to close. Please don't submit PRs that quietly "fix" the architecture; open an issue first if you think something should change structurally.
- **Small PRs over big ones.** A focused PR that does one thing is easier to review and merge than a large one that touches many files.

## Good first issues

If you're looking for a place to start, these are real gaps in the repo today — genuinely useful, and scoped small enough for a first PR:

1. **Add a GitHub Actions CI workflow** that runs `test_setup.py` on every push/PR. There's currently no CI at all — even a single job that installs `requirements.txt` and runs the setup check would catch broken dependency pins before they reach `main`.
2. **Add pytest unit tests for `src/chunker.py`.** It's a pure function (no API calls, no network), which makes it the easiest part of the pipeline to actually unit test — and right now it has zero test coverage.
3. **Add a `Dockerfile` for the FastAPI backend.** `docker-compose.yml` currently only covers MLflow + Postgres; there's no containerized path to run `shopbot/` itself, which is the first thing a lot of people reach for before Railway.
4. **Add a `GET /products/{id}` endpoint** to `src/api.py`. The frontend's product pages currently read catalog data directly rather than through the API — a real product-detail endpoint would make the backend a complete, self-contained API surface.
5. **Audit `.env.example` against `shopbot/README.md`** and add any environment variables the README references but the example file is missing (or vice versa).

Open an issue to claim one before starting, so two people don't end up duplicating work.

## Reporting bugs

Please include:
- What you ran (exact command) and what you expected vs. what happened
- Your Python/Node version
- Whether it reproduces on a clean clone (rules out local `venv`/`chroma_db` state issues)

## Pull requests

1. Fork, branch off `main`
2. Make your change; keep commits focused
3. If you touched `src/` or `evaluation/`, run `python test_setup.py` and confirm `python -m src.api` still starts cleanly
4. Open the PR with a short description of *why*, not just *what* — the reasoning is what makes review fast

## Questions

Open a discussion or issue on this repo — no question is too basic.
