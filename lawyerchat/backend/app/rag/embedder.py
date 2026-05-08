from sentence_transformers import SentenceTransformer

from app.config import settings


class Embedder:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model_name
        self.model = SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Text for embedding must not be empty")

        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embedding.astype(float).tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text or not text.strip() for text in texts):
            raise ValueError("Texts for embedding must not contain empty values")

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.astype(float).tolist()
