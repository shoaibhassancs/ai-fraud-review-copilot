FROM python:3.12-slim

# python:3.12-slim, not alpine: your .venv was built on Python 3.12 (visible
# in your own tracebacks -- .venv/lib/python3.12/site-packages), so matching
# that version avoids a "works on my machine, breaks in Docker" mismatch.
# alpine uses musl instead of glibc, and onnxruntime (a real dependency here,
# via chromadb) typically ships pre-built wheels for glibc, not musl --
# alpine would likely force a slow, failure-prone source build instead of a
# normal pip install.

WORKDIR /app

# Install dependencies before copying the rest of the code. pip install
# (especially chromadb/onnxruntime) is the slow step; copying code first
# would invalidate this cached layer on every code change, re-running the
# slow install on every rebuild. Copying requirements.txt first means
# code-only changes reuse the cached dependency layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Embed the knowledge base into Chroma at build time, not at container
# startup. chroma_db/ is git-ignored (derived, regenerable state) -- if we
# didn't do this, get_or_create_collection() wouldn't error, it would
# silently create an EMPTY collection on first run: retrieval returns
# nothing, the agent runs with no grounding, and nothing points at why.
# The four knowledge base docs are static and rarely change, so baking
# this in at build time matches the project's own "embed once, reuse"
# convention (src/retrieval.py) rather than inventing a different pattern
# for the container.
RUN python src/retrieval.py

EXPOSE 8000

# Must bind 0.0.0.0, not uvicorn's default 127.0.0.1. The default only
# accepts connections from inside the container itself -- a container
# that builds fine, runs fine, and is simply unreachable from outside.
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]