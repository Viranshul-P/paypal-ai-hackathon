FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# The classifier removes training sentences that are too close to the benchmark, so it needs this file.
COPY eval/scenarios ./eval/scenarios

RUN uv sync --frozen --no-dev && .venv/bin/python -m pauseline.prepare

# No persistent disk: demo data resets on every restart, which keeps the demo clean.
ENV PAUSELINE_DB=/tmp/pauseline.db \
    PAUSELINE_LLM_CACHE=/tmp/llm_cache.db

EXPOSE 8000
CMD ["sh", "-c", "exec .venv/bin/uvicorn pauseline.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
