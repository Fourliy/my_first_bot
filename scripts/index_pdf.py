"""Индексация PDF из ./data в ChromaDB. Уже проиндексированный файл пропускается."""

import asyncio
import hashlib
import logging
import sys
from pathlib import Path

import pymupdf4llm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.tools.rag import DATA_DIR, add_chunks, chunks_of, stored_hash
from my_first_bot.config import Config
from my_first_bot.llm_client import LLMClient
from my_first_bot.logger import setup_logger

logger = logging.getLogger("my_first_bot")


async def index_pdfs(llm: LLMClient) -> None:
    for pdf in sorted(DATA_DIR.glob("*.pdf")):
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        stored = await asyncio.to_thread(stored_hash, pdf.name)
        if stored == digest:
            logger.info("event=index_skip source=%s", pdf.name)
            continue
        markdown = await asyncio.to_thread(pymupdf4llm.to_markdown, str(pdf))
        chunks = chunks_of(markdown or "")
        if not chunks:
            logger.info("event=index_empty source=%s", pdf.name)
            continue
        vectors = await llm.embed(chunks)
        await asyncio.to_thread(add_chunks, pdf.name, digest, chunks, vectors)
        logger.info("event=index source=%s chunks=%s", pdf.name, len(chunks))


def main() -> None:
    config = Config()
    setup_logger(config.log_level)
    asyncio.run(index_pdfs(LLMClient(config)))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(f"Ошибка конфигурации: {error}. См. .env.example")
