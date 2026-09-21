"""get_vector_store and rerank are both faked here — a real run would hit
Chroma/Voyage and Cohere, all real (partly paid) external services. Faking
both lets this test suite check retriever.py's own composition/mapping logic
for free, independent of whether the embedding/reranking models themselves
are accurate."""

from dataclasses import dataclass, field

from langchain_core.documents import Document

from rag_service import retriever
from rag_service.reranker import RerankedHit


@dataclass
class _FakeStore:
    docs: list
    calls: list = field(default_factory=list)

    def similarity_search_with_score(self, query, k, filter=None):
        self.calls.append({"query": query, "k": k, "filter": filter})
        return [(doc, 0.1) for doc in self.docs]


def _doc(review_id, title_id, title, author, rating, text):
    return Document(
        page_content=text,
        metadata={
            "review_id": review_id,
            "title_id": title_id,
            "title": title,
            "author": author,
            "rating": rating,
            "chunk_index": 0,
        },
    )


def test_search_maps_reranked_hit_back_to_its_candidate(monkeypatch):
    docs = [
        _doc("r1", 1, "Movie A", "alice", 7.0, "chunk about the ending"),
        _doc("r2", 1, "Movie A", "bob", 9.0, "chunk about the acting"),
    ]
    fake_store = _FakeStore(docs=docs)
    monkeypatch.setattr(retriever, "get_vector_store", lambda: fake_store)
    monkeypatch.setattr(
        retriever,
        "rerank",
        lambda query, texts, top_n: [RerankedHit(index=1, relevance_score=0.95)],
    )

    results = retriever.search("was the ending good", top_n=1)

    assert results == [
        {
            "review_id": "r2",
            "title_id": 1,
            "title": "Movie A",
            "chunk_text": "chunk about the acting",
            "author": "bob",
            "rating": 9.0,
            "score": 0.95,
        }
    ]


def test_search_passes_title_id_as_chroma_filter(monkeypatch):
    fake_store = _FakeStore(docs=[])
    monkeypatch.setattr(retriever, "get_vector_store", lambda: fake_store)
    monkeypatch.setattr(retriever, "rerank", lambda query, texts, top_n: [])

    retriever.search("query", title_id=27205)

    assert fake_store.calls[0]["filter"] == {"title_id": 27205}


def test_search_no_filter_when_title_id_omitted(monkeypatch):
    fake_store = _FakeStore(docs=[])
    monkeypatch.setattr(retriever, "get_vector_store", lambda: fake_store)
    monkeypatch.setattr(retriever, "rerank", lambda query, texts, top_n: [])

    retriever.search("query")

    assert fake_store.calls[0]["filter"] is None
