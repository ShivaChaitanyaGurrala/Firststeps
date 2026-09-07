"""Connection to the Chroma vector store, run client-server via Docker
(not embedded in-process) — see config.py's chroma_host/chroma_port
docstring for the `docker run` command that starts it. Chroma is the one
store rag_service owns outright (the counterpart to data_service owning
Postgres) — nothing else in this project touches it directly.

Uses langchain_chroma's Chroma class (project decision, see the plan's M4
section) so the same retriever object this module hands back is directly
usable as a LangChain retriever in M5's LangGraph agent, without an adapter
layer — that's the actual reason LangChain glue was chosen here over a raw
chromadb.Client call.

pip install: langchain-chroma, chromadb (already in pyproject.toml; the
Chroma server itself runs in Docker, the client library just talks to it).
"""

from rag_service.config import settings
from rag_service.embeddings import get_embeddings
import chromadb
from langchain_chroma import Chroma


def get_vector_store():
    """Returns a langchain_chroma.Chroma instance bound to the movie_reviews
    collection.


    TODO(you):
        import chromadb
        from langchain_chroma import Chroma

        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        return Chroma(
            client=client,
            collection_name=settings.chroma_collection,
            embedding_function=VoyageEmbeddings(),  # or langchain_voyageai's, see embeddings.py
        )

    Confirm the Docker container is actually running first
    (`docker ps` should show tmdb-chroma) — a connection failure here means
    the container isn't up, not a code bug.
    """
    client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return Chroma(
        client=client,
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(model="voyage-4-lite"),
    )


def upsert_chunks(
    vector_store: Chroma,
    chunk_ids: list[str],
    texts: list[str],
    metadatas: list[dict],
) -> None:
    """Embed and store a batch of chunks.

    Takes an already-built vector_store (from one get_vector_store() call
    ingest.py makes once per run) instead of building its own — creating a
    fresh Chroma/Voyage client per review meant a fresh TCP+TLS handshake to
    both services on every single call, which is what turned this dev
    environment's known connection flakiness (see tmdb_client.py's retry
    comment) into an ~86% failure rate on a real run.

    langchain_chroma's add_texts handles calling the
    embedding_function for you; you don't call VoyageEmbeddings directly
    from here.

    ids matter: chunk_ids should be deterministic (e.g.
    f"{review_id}:{chunk_index}") so re-running ingest.py on an
    already-embedded review overwrites its old chunks instead of duplicating
    them — Chroma's add_texts upserts by id.

    metadatas: one dict per chunk, with review_id/title_id/chunk_index PLUS
    the denormalized title/author/rating pulled from data_service's
    ReviewOut — this is the M4 architecture decision that keeps retriever.py
    able to answer a search entirely from Chroma, with no call back to
    data_service on the query path. The tradeoff you're accepting: if a
    review's title/author/rating ever changed in Postgres after ingestion,
    Chroma's copy would go stale until the next re-ingest — acceptable here
    since none of those fields are expected to change after a review is
    posted.
    """
    vector_store.add_texts(texts=texts, metadatas=metadatas, ids=chunk_ids)


def existing_review_ids(vector_store: Chroma) -> set[str]:
    """review_id values already present in Chroma's metadata, so ingest.py
    can skip reviews it has already embedded instead of re-embedding the
    whole catalog on every run (the "only embed reviews that changed"
    TODO from this module's original design notes).

    Pulls every stored metadata dict in one call — fine at this project's
    scale (low thousands of chunks); would need paging via get()'s
    limit/offset if the collection ever grew large enough for that to
    matter.
    """
    result = vector_store.get(include=["metadatas"])
    return {
        metadata["review_id"]
        for metadata in result["metadatas"]
        if metadata and "review_id" in metadata
    }
