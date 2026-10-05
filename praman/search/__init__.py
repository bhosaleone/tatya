"""Marathi Search Engine and Curated Web Directory.

Features:
- Marathi-only Full-Text Search (FTS5 + BM25)
- Matra-safe tokenization and morphological suffix normalization
- Hybrid Ranking: BM25 + Domain PageRank + Devanagari Integrity Ratio
- Curated Topic Directory (News, Finance, Agri, Govt, Wiki, Literature, Blogs)
- Multi-threaded Local Search Server and Web UI
"""

from praman.search.engine import MarathiSearchEngine, SearchResultItem
from praman.search.directory import MarathiDirectory, DirectoryCategory
from praman.search.indexer import SearchIndexer

__all__ = [
    "MarathiSearchEngine",
    "SearchResultItem",
    "MarathiDirectory",
    "DirectoryCategory",
    "SearchIndexer",
]
