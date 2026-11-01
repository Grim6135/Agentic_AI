"""
TRIPPY Backend — RAG Retrieval & Knowledge Base Tests

Tests:
1. Ingestion pipeline: cleaning and chunking with frontmatter metadata preservation.
2. Retrieval relevance: matching semantic queries to appropriate destination passages.
3. Source label preservation in retrieved results.
4. Graceful handling of empty or missing knowledge bases.
"""

from pathlib import Path
import pytest

from app.rag.pipeline import (
    RAGKnowledgeBase,
    chunk_document,
    parse_frontmatter,
)


def test_parse_frontmatter():
    sample = """---
destination: Kyoto, Japan
source: Kyoto Heritage & Cultural Travel Guide (2026)
category: Culture
---

# Kyoto Guide
Content here
"""
    meta, body = parse_frontmatter(sample)
    assert meta["destination"] == "Kyoto, Japan"
    assert meta["source"] == "Kyoto Heritage & Cultural Travel Guide (2026)"
    assert meta["category"] == "Culture"
    assert "# Kyoto Guide" in body


def test_chunk_document_preserves_metadata(tmp_path: Path):
    guide_file = tmp_path / "test_guide.md"
    guide_file.write_text(
        """---
destination: TestCity, Wonderland
source: Test Official Guide (2026)
category: Adventure
---

# TestCity Overview

## Historic Quarter
Ancient cobblestone streets and centuries-old bell towers.

## Culinary Delights
Famous for artisanal pastries and hand-pulled noodles.
""",
        encoding="utf-8",
    )

    chunks = chunk_document(guide_file)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.destination == "TestCity, Wonderland"
        assert chunk.source == "Test Official Guide (2026)"
        assert chunk.category == "Adventure"
        assert chunk.section in ["Historic Quarter", "Culinary Delights", "Overview"]


def test_retrieval_relevance_and_source_labels():
    """Verify semantic retrieval returns relevant documents with source citations."""
    kb = RAGKnowledgeBase(collection_name="test_relevance_kb")
    count = kb.ingest_directory()
    assert count > 0

    # Query for temples & cultural shrines
    passages = kb.retrieve(query="Buddhist temples shrines and torii gates", top_k=2)
    assert len(passages) > 0
    # Must retrieve Kyoto passages
    assert any("Kyoto" in p.destination for p in passages)
    # Must preserve source metadata
    assert all(len(p.source) > 0 for p in passages)
    assert all(len(p.section) > 0 for p in passages)
    assert all(p.score >= 0.0 for p in passages)


def test_retrieval_filtered_by_destination():
    """Verify destination filtering works as expected."""
    kb = RAGKnowledgeBase(collection_name="test_filter_kb")
    kb.ingest_directory()

    rome_passages = kb.retrieve(query="classical architecture and monuments", destination="Rome, Italy", top_k=3)
    assert len(rome_passages) > 0
    assert all("Rome" in p.destination for p in rome_passages)
    assert any("Rome Essential Explorer Guide" in p.source for p in rome_passages)


def test_empty_knowledge_base_handling(tmp_path: Path):
    """Verify empty or non-existent knowledge bases return empty list without crashing."""
    empty_kb = RAGKnowledgeBase(collection_name="test_empty_kb")
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    ingested = empty_kb.ingest_directory(data_dir=empty_dir)
    assert ingested == 0

    results = empty_kb.retrieve(query="any search term", top_k=3)
    assert results == []


def test_missing_directory_handling():
    """Verify non-existent directory returns 0 without raising exception."""
    kb = RAGKnowledgeBase(collection_name="test_missing_dir_kb")
    fake_dir = Path("/nonexistent/directory/path/for/trippy")
    count = kb.ingest_directory(data_dir=fake_dir)
    assert count == 0
