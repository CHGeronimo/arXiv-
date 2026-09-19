#!/usr/bin/env python3
"""流水线模式：边抓边分析——并行重叠验证 + 计数正确性 + 中断续跑语义保持。"""
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from backend.db import init_db  # noqa: E402
init_db()

from backend.crawler.models import Paper  # noqa: E402
from backend.jobs import BaseCrawlerJob  # noqa: E402


def _paper(i):
    return Paper(id=f"pipe-{i}", source="test", title=f"Paper {i}", summary=f"abstract {i}")


class _FakeCrawler:
    def __init__(self, n, crawl_delay=0.02):
        self.n, self.crawl_delay = n, crawl_delay

    def crawl_iter(self):
        for i in range(self.n):
            time.sleep(self.crawl_delay)  # 模拟网络抓取耗时
            yield _paper(i)


class _PipeJob(BaseCrawlerJob):
    name = "pipetest"
    def __init__(self, crawler):
        self._c = crawler
    def _create_crawler(self, subs):
        return self._c
    def _post_run(self, subs, fetched_info):
        self.post_info = fetched_info


processed = []
_process_delay = [0.0]


def _fake_append(paper, enhance=False):
    time.sleep(_process_delay[0])  # 模拟 AI 处理耗时
    processed.append(paper.id)
    return "written"


# [1] 并行重叠：30 篇×抓取0.02s×处理0.08s。串行=30×0.10=3.0s；
#     流水线理想≈max(30×0.02, 30×0.08/5 workers)=0.6s。断言 <1.5s 即证重叠。
processed.clear()
_process_delay[0] = 0.08
job = _PipeJob(_FakeCrawler(30))
t0 = time.monotonic()
with patch("backend.jobs.append_paper", _fake_append), \
     patch("backend.jobs._ai_max_workers", 5):
    job.run()
elapsed = time.monotonic() - t0
assert len(processed) == 30, f"应处理 30 篇, 实际 {len(processed)}"
assert elapsed < 1.5, f"流水线应并行重叠，耗时 {elapsed:.2f}s 过长（串行≈3.0s）"
print(f"[1] 边抓边分析并行重叠 ✓（30 篇 {elapsed:.2f}s，串行需 ≈3.0s）")

# [2] 结果分类计数：exists/filter_reject 正确归账 + 最终状态 done
processed.clear()
_process_delay[0] = 0.0
calls = {"n": 0}
def _fake_append2(paper, enhance=False):
    calls["n"] += 1
    return "exists" if paper.id.endswith("9") else "written"
job2 = _PipeJob(_FakeCrawler(25))
with patch("backend.jobs.append_paper", _fake_append2), \
     patch("backend.jobs._ai_max_workers", 4):
    job2.run()
assert calls["n"] == 25
from backend.jobs import get_job_status
st = get_job_status().get("pipetest", {})
assert st.get("status") == "done" and "23 接受" in st.get("message", ""), st  # pipe-9/pipe-19 两篇 exists
print("[2] 计数与完成状态 ✓（23 接受 / 2 重复）")

# [3] 爬取中途异常：已抓取部分仍被处理，任务不崩
processed.clear()
_process_delay[0] = 0.0
class _BoomCrawler:
    def crawl_iter(self):
        yield _paper(0)
        yield _paper(1)
        raise RuntimeError("network down mid-crawl")
job3 = _PipeJob(_BoomCrawler())
with patch("backend.jobs.append_paper", _fake_append), \
     patch("backend.jobs._ai_max_workers", 2):
    job3.run()
assert sorted(processed) == ["pipe-0", "pipe-1"], processed
print("[3] 爬取中断已抓部分照常处理 ✓")

print("\n流水线模式测试通过 ✅")
