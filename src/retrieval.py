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

    # Verify against the collection's actual state, not just the input list —
    # a silent partial failure would still print success if we only counted
    # what we intended to write.
    stored = collection.get(ids=ids)
    stored_ids = set(stored["ids"])
    expected_ids = set(ids)
    if stored_ids != expected_ids:
        missing = expected_ids - stored_ids
        raise RuntimeError(
            f"Upsert did not persist correctly — missing ids: {missing}"
        )

    print(f"Embedded {len(stored_ids)} docs into collection '{COLLECTION_NAME}' (verified against collection.get):")
    for path in md_files:
        print(f"  - {path.name}")


def query_knowledge_base(query_text, n_results=1):
    """
    Query the fraud-pattern collection and return the top n_results matches.

    Note on distance: this collection uses Chroma's default metric (L2),
    not cosine — LOWER distance means MORE similar, not higher.
    """
    collection = get_collection()
    results = collection.query(query_texts=[query_text], n_results=n_results)
    return results


def _print_query_result(query_text, n_results=2):
    results = query_knowledge_base(query_text, n_results=n_results)
    ids = results["ids"][0]
    distances = results["distances"][0]
    print(f'Query: "{query_text}"')
    for doc_id, dist in zip(ids, distances):
        print(f"    {doc_id}  (distance: {dist:.4f})")
    print()


if __name__ == "__main__":
    embed_knowledge_base()

    print("\n--- Tier 1: naive flag_reason strings ---\n")
    for q in ["velocity_spike", "geo_anomaly", "amount_spike", "new_merchant_category"]:
        _print_query_result(q)

    print("--- Tier 2: realistic natural-language queries ---\n")
    for q in [
        "Multiple transactions happened within a short time window",
        "The transaction occurred somewhere far from the customer's home location",
        "The transaction amount is much higher than this customer normally spends",
        "The customer made a purchase in a merchant category they've never used before",
    ]:
        _print_query_result(q)