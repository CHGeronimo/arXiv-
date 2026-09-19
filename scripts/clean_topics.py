#!/usr/bin/env python3
"""一次性清洗 profile 中的 liked/disliked 主题（双语重复归并为中文规范表述）。

⚠️ 先重启 daemon（新去重代码）并在无点赞操作时运行，否则旧 daemon 的
后台线程会覆盖清洗结果。

用法：python scripts/clean_topics.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dotenv  # noqa: E402

dotenv.load_dotenv("backend/ai/.env")

import backend.api as api  # noqa: E402

prof_path = Path("research_profile.json")
prof = json.loads(prof_path.read_text(encoding="utf-8"))

for key in ("liked_topics", "disliked_topics"):
    before = prof.get(key, [])
    if len(before) <= 3:
        print(f"{key}: {len(before)} 条，跳过")
        continue
    cleaned = api._deduplicate_topics(before)
    print(f"{key}: {len(before)} → {len(cleaned)} 条")
    for t in cleaned:
        print(f"  - {t}")
    prof[key] = cleaned

tmp = prof_path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, prof_path)
print("\n✓ 已写回 research_profile.json（原子写）")
