"""
Embedding setup for AI Fraud-Review Copilot.

Reads the four fraud-pattern docs from knowledge_base/ and loads them into
a persistent Chroma collection, so the agent can retrieve the right one at
query time (Day 3).

Simplest version on purpose: one embedding call per doc, one collection,
no chunking, no tuning. Chroma's default embedding function
(all-MiniLM-L6-v2, run locally via ONNX) applies automatically since none
is specified — no API key, no network call, nothing extra to install
(onnxruntime is already a transitive dependency of chromadb).

Run from the project root:
    python src/retrieval.py
"""

from pathlib import Path

import chromadb

KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"
CHROMA_DB_PATH = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "fraud_patterns"


def get_collection():
    """Create (or get) the persistent Chroma collection for fraud-pattern docs."""
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    # No embedding_function specified — Chroma's default (all-MiniLM-L6-v2) applies.
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return collection


def embed_knowledge_base():
    """Read every .md file in knowledge_base/ and add it to the collection."""
    collection = get_collection()

    md_files = sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No .md files found in {KNOWLEDGE_BASE_DIR}")

    ids = []
    documents = []
    metadatas = []

    for path in md_files:
        ids.append(path.stem)  # e.g. "velocity_fraud"
        documents.append(path.read_text())
        metadatas.append({"source": path.name})  # e.g. "velocity_fraud.md"

    # upsert (not add) so re-running this script after editing a doc
    # updates the existing entry instead of erroring on a duplicate id.
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    print(f"Embedded {len(md_files)} docs into collection '{COLLECTION_NAME}':")
    for path in md_files:
        print(f"  - {path.name}")


if __name__ == "__main__":
    embed_knowledge_base()