from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional

__all__ = ["Journal", "Subscriptions"]


@dataclass
class Journal:
    issn: str
    name: str
    last_updated: Optional[str] = None


@dataclass
class Subscriptions:
    arxiv_categories: List[str] = field(default_factory=lambda: ["cs.CV", "cs.CL"])
    crossref_journals: List[Journal] = field(default_factory=list)

    @classmethod
    def load(cls, path: str = "subscriptions.json") -> Subscriptions:
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cats = data.get("arxiv", {}).get("categories", ["cs.CV", "cs.CL"])
        journals = [
            Journal(issn=j["issn"], name=j["name"], last_updated=j.get("lastUpdated"))
            for j in data.get("crossref", {}).get("journals", [])
        ]
        return cls(arxiv_categories=cats, crossref_journals=journals)

    def save(self, path: str = "subscriptions.json") -> None:
        data = {
            "arxiv": {"categories": self.arxiv_categories},
            "crossref": {
                "journals": [
                    {
                        "issn": j.issn,
                        "name": j.name,
                        "lastUpdated": j.last_updated,
                    }
                    for j in self.crossref_journals
                ]
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "arxiv": {"categories": self.arxiv_categories},
            "crossref": {
                "journals": [
                    {"issn": j.issn, "name": j.name, "lastUpdated": j.last_updated}
                    for j in self.crossref_journals
                ]
            },
        }
