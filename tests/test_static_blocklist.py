#!/usr/bin/env python3
"""P0-1: static route must not serve secrets (.env/db/logs)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api  # noqa: E402

c = api.app.test_client()

for path in ["/ai/.env", "/data/papers.db", "/logs/arxivsci.log", "ai/.env", ".git/config"]:
    r = c.get(f"/{path}" if not path.startswith("/") else path)
    assert r.status_code == 403, f"{path} 应 403, got {r.status_code}"

for path in ["/js/app.js", "/css/tokens.css", "/index.html"]:
    r = c.get(path)
    assert r.status_code == 200, f"{path} 应 200, got {r.status_code}"

print("静态路由黑名单测试通过 ✅")
