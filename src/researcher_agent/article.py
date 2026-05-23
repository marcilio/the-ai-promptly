from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ArticleRecord:
    url: str
    title: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    category: str = "other"
    relevance_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    first_seen: Optional[str] = None
    last_included: Optional[str] = None
    source_url: Optional[str] = None
    minhash: Optional[List[int]] = None
    takeaways: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "published_at": self.published_at,
            "summary": self.summary,
            "content": self.content,
            "category": self.category,
            "relevance_score": self.relevance_score,
            "tags": self.tags,
            "takeaways": self.takeaways,
            "first_seen": self.first_seen,
            "last_included": self.last_included,
            "source_url": self.source_url,
            "minhash": self.minhash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArticleRecord":
        return cls(
            url=data.get("url"),
            title=data.get("title"),
            author=data.get("author"),
            published_at=data.get("published_at"),
            summary=data.get("summary"),
            content=data.get("content"),
            category=data.get("category", "other"),
            relevance_score=data.get("relevance_score", 0.0),
            tags=data.get("tags", []),
            takeaways=data.get("takeaways") or [],
            first_seen=data.get("first_seen"),
            last_included=data.get("last_included"),
            source_url=data.get("source_url"),
            minhash=data.get("minhash"),
        )
