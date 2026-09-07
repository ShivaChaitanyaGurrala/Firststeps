"""Constructing VoyageAIEmbeddings doesn't make a network call (verified
against the installed SDK: its model_validator only builds a
voyageai.Client, which just sets up a requests.Session) — only an actual
.embed_query()/.embed_documents() call would hit the network. Safe to
construct for real here."""

import pytest
from langchain_voyageai import VoyageAIEmbeddings

from rag_service.config import settings
from rag_service.embeddings import get_embeddings


def test_raises_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "voyage_api_key", "")
    with pytest.raises(RuntimeError, match="VOYAGE_API_KEY"):
        get_embeddings()


def test_returns_configured_embeddings_when_key_present(monkeypatch):
    monkeypatch.setattr(settings, "voyage_api_key", "fake-key-for-test")
    embeddings = get_embeddings(model="voyage-4-lite")
    assert isinstance(embeddings, VoyageAIEmbeddings)
    assert embeddings.model == "voyage-4-lite"
