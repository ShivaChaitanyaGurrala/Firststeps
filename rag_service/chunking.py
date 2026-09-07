"""Split review text into overlapping chunks for embedding.

Why chunk at all: a whole review can run to several paragraphs, but an
embedding vector represents ONE point in semantic space for the whole text
you feed it — cram a long, multi-topic review into a single embedding and
its vector blurs into an average of everything it's about, which hurts
retrieval precision for a query about one specific point in it. Chunking
trades that off against context: too small a chunk (e.g. one sentence) and
you lose the surrounding context a sentence needs to make sense on its own.

Uses LangChain's RecursiveCharacterTextSplitter (a project-level decision,
see the plan doc's M4 section) rather than a hand-rolled splitter — it tries
a list of separators in order (paragraph breaks, then lines, then
sentences, then words) and only falls back to a harder split when a chunk
is still too big, which keeps chunks from cutting mid-sentence when it can
avoid it.

pip install: langchain-text-splitters (already in pyproject.toml).
"""

from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class ReviewChunk:
    review_id: str
    title_id: int
    chunk_index: int
    text: str


def chunk_review(review_id: str, title_id: int, content: str) -> list[ReviewChunk]:
    """Split one review's content into ReviewChunks.

    TODO(you):
    1. `from langchain_text_splitters import RecursiveCharacterTextSplitter`
    2. Instantiate it with a chunk_size/chunk_overlap you choose — start
       around chunk_size=500-800 characters, chunk_overlap=50-100 (overlap
       exists so a sentence split across a chunk boundary still appears in
       full in at least one chunk). These are a starting point, not a
       prescribed answer — tune them once you see real retrieval results.
    3. Call `.split_text(content)` to get a list[str], then wrap each piece
       in a ReviewChunk with review_id, title_id, and its index in the list
       (chunk_index matters for reconstructing chunk order later, e.g. in a
       debug view — it's not used for retrieval itself).
    """
    text_splitter = RecursiveCharacterTextSplitter(
       chunk_size=400,
       chunk_overlap=100)
    review_chunks = text_splitter.split_text(content)

    return [
        ReviewChunk(
            review_id=review_id,
            title_id=title_id,
            chunk_index=i,
            text=chunk
        )
        for i, chunk in enumerate(review_chunks)
    ]
