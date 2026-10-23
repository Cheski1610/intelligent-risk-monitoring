"""Citation-preserving local lexical retrieval with TF-IDF."""
from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from irml.audit_assistant.documents import DocumentChunk

SPANISH_STOP_WORDS = {
    "para", "como", "desde", "hasta", "sobre", "entre", "cuando", "donde",
    "este", "esta", "estos", "estas", "una", "uno", "unos", "unas", "por",
    "con", "sin", "del", "las", "los", "que", "una", "sus", "ser", "se",
    "al", "y", "o", "de", "la", "el", "en", "un", "es", "no", "si",
}


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class LexicalRetriever:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            stop_words=list(SPANISH_STOP_WORDS),
            token_pattern=r"(?u)\b[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ]{2,}\b",
        )
        self.matrix = (
            self.vectorizer.fit_transform([chunk.text for chunk in chunks])
            if chunks
            else None
        )

    def search(self, query: str, *, limit: int = 5) -> list[RetrievedChunk]:
        if not self.chunks or self.matrix is None or not query.strip():
            return []
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        indices = scores.argsort()[::-1]
        return [
            RetrievedChunk(self.chunks[index], float(scores[index]))
            for index in indices[:limit]
            if scores[index] > 0
        ]
