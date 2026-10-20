import asyncio
import logging
from pathlib import Path

logger = logging.getLogger("my_first_bot")

DATA_DIR = Path("data")
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION = "company"
CHUNK_CHARS = 800
NOT_FOUND = "В документах компании ничего не найдено. Не выдумывай ответ."


def chunks_of(text: str) -> list[str]:
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    buffer = ""
    for part in parts:
        if len(part) > CHUNK_CHARS:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            for start in range(0, len(part), CHUNK_CHARS):
                chunks.append(part[start : start + CHUNK_CHARS])
            continue
        if buffer and len(buffer) + len(part) + 2 > CHUNK_CHARS:
            chunks.append(buffer)
            buffer = part
        else:
            buffer = f"{buffer}\n\n{part}" if buffer else part
    if buffer:
        chunks.append(buffer)
    return chunks


def collection():
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION, metadata={"hnsw:space": "cosine"})


def stored_hash(source: str) -> str | None:
    found = collection().get(where={"source": source}, include=["metadatas"], limit=1)
    metadatas = found.get("metadatas") or []
    if not metadatas:
        return None
    return metadatas[0].get("sha256")


def add_chunks(source: str, digest: str, chunks: list[str], vectors: list[list[float]]) -> None:
    store = collection()
    existing = store.get(where={"source": source}, include=[])
    if existing.get("ids"):
        store.delete(where={"source": source})
    store.add(
        ids=[f"{source}:{digest[:8]}:{index}" for index in range(len(chunks))],
        documents=chunks,
        embeddings=vectors,
        metadatas=[{"source": source, "sha256": digest} for _ in chunks],
    )


def _nearest(vector: list[float], n_results: int) -> list[tuple[str, str]]:
    store = collection()
    count = store.count()
    if count == 0:
        return []
    found = store.query(
        query_embeddings=[vector],
        n_results=min(n_results, count),
        include=["documents", "metadatas"],
    )
    documents = (found.get("documents") or [[]])[0]
    metadatas = (found.get("metadatas") or [[]])[0]
    return [(meta.get("source", ""), text) for text, meta in zip(documents, metadatas) if text]


async def rag_search(query: str, n_results: int = 4) -> str:
    """Ближайшие фрагменты PDF компании. n_results — сколько фрагментов вернуть."""
    query = (query or "").strip()
    if not query:
        return "Пустой запрос. Уточни, что искать в документах."
    n_results = max(1, min(int(n_results), 10))
    from my_first_bot.config import Config
    from my_first_bot.llm_client import LLMClient

    vector = (await LLMClient(Config()).embed([query]))[0]
    hits = await asyncio.to_thread(_nearest, vector, n_results)
    if not hits:
        return NOT_FOUND
    return "\n\n".join(f"[{source}] {text}" for source, text in hits)
