from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional

__all__ = ["Paper"]


@dataclass
class Paper:
    id: str
    source: str  # "arxiv" or "crossref"
    title: str
    summary: str
    authors: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    doi: str = ""
    published_date: str = ""
    url: str = ""
    pdf: str = ""
    publisher: str = ""
    journal_title: Optional[str] = None
    issn: List[str] = field(default_factory=list)
    comment: Optional[str] = None
    article_type: str = ""  # "research" or "news"

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_jsonl(cls, line: str) -> Paper:
        data = json.loads(line)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
