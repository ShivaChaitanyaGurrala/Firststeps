"""Shared fixtures for rag_service's test suite.

Everything here is designed to run with zero real network calls to
data_service, Chroma's Docker container, Voyage, or Cohere — those are all
real (partly paid) external services rag_service talks to, and a test suite
that hits them for real on every `pytest` run would cost money/quota and
require Docker just to run tests, unlike data_service's suite which only
needs a local test Postgres.
"""

import uuid

import chromadb
import pytest
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings


class FakeEmbeddings(Embeddings):
    """Deterministic, free stand-in for VoyageAIEmbeddings. Returns a fixed
    small vector derived from text length, not meaning — nothing under test
    here depends on embeddings being semantically meaningful, only on
    add_texts/get actually round-tripping through a real Chroma collection.
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text) % 7), float(len(text) % 11), 0.0]


@pytest.fixture()
def fake_vector_store() -> Chroma:
    """A real (in-memory, no Docker) Chroma collection wired to
    FakeEmbeddings instead of Voyage — exercises the actual
    langchain_chroma add_texts/get code paths vector_store.py relies on,
    without a running tmdb-chroma container or a paid embedding call.

    A fresh EphemeralClient() per test is NOT enough isolation by itself —
    verified that chromadb's ephemeral backing store is shared per-process,
    so two EphemeralClient() instances in the same pytest run can see each
    other's collections if they share a name. A random collection_name per
    test is what actually isolates them.
    """
    return Chroma(
        client=chromadb.EphemeralClient(),
        collection_name=f"test_reviews_{uuid.uuid4().hex}",
        embedding_function=FakeEmbeddings(),
    )
