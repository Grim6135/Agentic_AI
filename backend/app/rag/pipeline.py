"""
TRIPPY Backend — RAG Ingestion & Vector Retrieval Pipeline

Ingests curated destination guidebooks, cleans & chunks text,
generates normalized vector embeddings, and stores them in ChromaDB.
Provides semantic retrieval with preserved source metadata and
gracefully handles empty or unavailable knowledge bases.
"""

import hashlib
import logging
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from app.config import settings

logger = logging.getLogger("trippy.rag")


# ─── Data Models ─────────────────────────────────────────────────────────

class RetrievedPassage(BaseModel):
    """Passage retrieved from the curated vector knowledge base."""
    text: str
    destination: str
    source: str
    section: str
    category: str = "General"
    score: float = 0.0


class DocumentChunk(BaseModel):
    """Chunk of a guidebook with rich source metadata."""
    chunk_id: str
    text: str
    destination: str
    source: str
    title: str
    section: str
    category: str


# ─── Deterministic Normalized Embedding Function ──────────────────────────

class LocalSemanticEmbeddingFunction(EmbeddingFunction):
    """
    Fast, deterministic, normalized n-gram semantic embedding generator.
    Produces 128-dimensional L2-normalized embeddings without external network calls
    or bulky model downloads, ensuring 100% offline & test reliability.
    """

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def name(self) -> str:
        return "local_semantic_embedding"


    def __call__(self, input: Documents) -> Embeddings:
        embeddings: Embeddings = []
        for doc in input:
            vec = [0.0] * self.dimensions
            # Tokenize words and character 3-grams
            words = re.findall(r"\w+", doc.lower())
            for word in words:
                idx = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % self.dimensions
                vec[idx] += 1.0
                # Add sub-word ngrams for morphological overlap
                for i in range(len(word) - 2):
                    ngram = word[i : i + 3]
                    n_idx = int(hashlib.sha256(ngram.encode("utf-8")).hexdigest(), 16) % self.dimensions
                    vec[n_idx] += 0.5

            # L2 normalization
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]
            embeddings.append(vec)
        return embeddings


# ─── Chunker & Parser ────────────────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[Dict[str, str], str]:
    """Extracts yaml-like frontmatter metadata and remaining markdown body."""
    meta = {}
    body = content.strip()
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body


def chunk_document(
    file_path: Path,
    chunk_size: int = 450,
    overlap: int = 50,
) -> List[DocumentChunk]:
    """
    Cleans and chunks a markdown guidebook into semantic section-aware blocks.
    """
    content = file_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    destination = meta.get("destination", file_path.stem.replace("_guide", "").title())
    source = meta.get("source", f"{destination} Curated Guide")
    category = meta.get("category", "General")
    title = meta.get("title", f"{destination} Travel Guide")

    # Split by markdown ## headings
    sections = re.split(r"\n(?=##\s+)", body)
    chunks: List[DocumentChunk] = []

    for sec_idx, sec_text in enumerate(sections):
        lines = sec_text.strip().splitlines()
        if not lines:
            continue
        section_name = lines[0].replace("#", "").strip() if lines[0].startswith("#") else "Overview"
        clean_text = "\n".join(lines[1:]).strip() if lines[0].startswith("#") else sec_text.strip()

        # Split large sections into smaller paragraph windows if necessary
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        current_chunk = ""

        for p_idx, p in enumerate(paragraphs):
            if len(current_chunk) + len(p) <= chunk_size:
                current_chunk = f"{current_chunk}\n\n{p}".strip()
            else:
                if current_chunk:
                    cid = f"{file_path.stem}_{sec_idx}_{len(chunks)}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=cid,
                            text=current_chunk,
                            destination=destination,
                            source=source,
                            title=title,
                            section=section_name,
                            category=category,
                        )
                    )
                current_chunk = p

        if current_chunk:
            cid = f"{file_path.stem}_{sec_idx}_{len(chunks)}"
            chunks.append(
                DocumentChunk(
                    chunk_id=cid,
                    text=current_chunk,
                    destination=destination,
                    source=source,
                    title=title,
                    section=section_name,
                    category=category,
                )
            )

    return chunks


# ─── Vector Knowledge Base Manager ───────────────────────────────────────

class RAGKnowledgeBase:
    """
    ChromaDB-backed vector store manager for destination guides.
    """

    def __init__(self, collection_name: str = "trippy_destinations"):
        self.collection_name = collection_name
        self.embedding_fn = LocalSemanticEmbeddingFunction()
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "TRIPPY Curated Destination Guides"},
        )
        self.total_documents = 0

    def ingest_directory(self, data_dir: Optional[Path] = None) -> int:
        """
        Ingests all guidebook files from the given directory into ChromaDB.
        Gracefully handles empty or missing directories.
        """
        if data_dir is None:
            # Default to backend/app/rag/data relative to this file
            data_dir = Path(__file__).parent / "data"

        if not data_dir.exists() or not data_dir.is_dir():
            logger.warning(f"RAG knowledge base directory not found: {data_dir}")
            return 0

        guide_files = list(data_dir.glob("*.md")) + list(data_dir.glob("*.txt"))
        if not guide_files:
            logger.info(f"No guidebook files found in {data_dir}.")
            return 0

        all_chunks: List[DocumentChunk] = []
        for file in guide_files:
            try:
                chunks = chunk_document(file)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Error parsing guide file {file}: {e}")

        if not all_chunks:
            return 0

        # Add to Chroma collection
        ids = [c.chunk_id for c in all_chunks]
        documents = [f"{c.title} - {c.section}\n{c.text}" for c in all_chunks]
        metadatas = [
            {
                "destination": c.destination,
                "source": c.source,
                "section": c.section,
                "category": c.category,
                "title": c.title,
            }
            for c in all_chunks
        ]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        self.total_documents = len(all_chunks)
        logger.info(f"Successfully ingested {self.total_documents} chunks into Chroma collection.")
        return self.total_documents

    def retrieve(
        self,
        query: str,
        destination: Optional[str] = None,
        top_k: int = 3,
    ) -> List[RetrievedPassage]:
        """
        Searches ChromaDB for relevant passages matching the query.
        Filters by destination when provided.
        Returns empty list on empty knowledge base or errors.
        """
        if self.collection.count() == 0:
            return []

        city_clean = destination.split(",")[0].strip() if destination else None
        results = None

        if destination:
            # 1. Try exact destination filter
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(top_k, self.collection.count()),
                    where={"destination": destination},
                )
            except Exception:
                results = None

            # 2. Try city name filter
            if (not results or not results.get("documents") or not results["documents"][0]) and city_clean and city_clean != destination:
                try:
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=min(top_k, self.collection.count()),
                        where={"destination": city_clean},
                    )
                except Exception:
                    results = None

        # 3. If no destination filter was requested, query standard
        if not destination:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(top_k, self.collection.count()),
                )
            except Exception as e:
                logger.warning(f"Chroma query error: {e}")
                return []

        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        passages: List[RetrievedPassage] = []
        for idx, doc_text in enumerate(docs):
            meta = metas[idx] if idx < len(metas) else {}
            dist = distances[idx] if idx < len(distances) else 1.0
            doc_dest = meta.get("destination", "General")

            # Strict destination guard: If a destination was requested, ensure the document belongs to it
            if destination:
                dest_lower = destination.lower()
                doc_dest_lower = doc_dest.lower()
                city_lower = (city_clean or "").lower()
                if not (city_lower in doc_dest_lower or doc_dest_lower in dest_lower):
                    continue

            # Convert cosine distance to approximate similarity score
            score = max(0.0, round(1.0 - (dist / 2.0), 3))

            passages.append(
                RetrievedPassage(
                    text=doc_text,
                    destination=doc_dest,
                    source=meta.get("source", "Verified Curated Guidebook"),
                    section=meta.get("section", "Overview"),
                    category=meta.get("category", "General"),
                    score=score,
                )
            )

        return passages


# Singleton instance
rag_service = RAGKnowledgeBase()
# Ingest baseline guidebooks upon module load if enabled
if settings.rag_enabled:
    try:
        rag_service.ingest_directory()
    except Exception as exc:
        logger.warning(f"Initial RAG ingestion deferred: {exc}")
