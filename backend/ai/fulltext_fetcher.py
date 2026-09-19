"""Fetch and extract full text from arXiv papers via ar5iv.org."""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

AR5IV_BASE = "https://ar5iv.org/html/"


def fetch_arxiv_html(arxiv_id: str, timeout: int = 30) -> Optional[str]:
    """Fetch HTML content of an arXiv paper from ar5iv.org.

    Returns raw HTML string, or None on failure.
    """
    url = f"{AR5IV_BASE}{arxiv_id}"
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
        logger.warning(f"ar5iv 对 {arxiv_id} 返回 {resp.status_code}")
        return None
    except Exception as e:
        logger.warning(f"获取 {arxiv_id} 的 ar5iv HTML 失败: {e}")
        return None


# Section name patterns for extraction
_SECTION_PATTERNS = [
    (r"\bintroduction\b", "introduction"),
    (r"\bmethod(s|ology)?\b", "method"),
    (r"\bapproach\b", "method"),
    (r"\bexperiment(s|al)?\b", "experiments"),
    (r"\bevaluation\b", "experiments"),
    (r"\bresult(s)?\b", "experiments"),
    (r"\bconclusion(s)?\b", "conclusion"),
    (r"\bdiscussion\b", "conclusion"),
    (r"\blimitation(s)?\b", "limitations"),
    (r"\bfuture work\b", "limitations"),
]


def _classify_heading(text: str) -> Optional[str]:
    """Map a heading text to a section category."""
    # Strip leading section numbers (e.g. "1Introduction" -> "Introduction")
    lower = re.sub(r"^[\d.]+\s*", "", text.lower().strip())
    for pattern, category in _SECTION_PATTERNS:
        if re.search(pattern, lower):
            return category
    return None


def extract_sections(html: str) -> dict[str, str]:
    """Extract paper sections from ar5iv HTML.

    Returns dict mapping section names to their text content:
    {"introduction": "...", "method": "...", "experiments": "...",
     "conclusion": "...", "limitations": "..."}
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove style, script, and math elements (keep text)
    for tag in soup.find_all(["style", "script", "math", "svg"]):
        tag.decompose()

    sections: dict[str, list[str]] = {}
    current_section: Optional[str] = None
    current_text: list[str] = []

    # Walk through all elements in document order
    for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol"]):
        if element.name in ("h1", "h2", "h3", "h4"):
            # Save previous section
            if current_section and current_text:
                sections.setdefault(current_section, []).append(" ".join(current_text))
                current_text = []

            # Classify new heading
            heading_text = element.get_text(strip=True)
            current_section = _classify_heading(heading_text)
            continue

        if current_section is None:
            continue

        text = element.get_text(strip=True)
        if text and len(text) > 20:
            current_text.append(text)

    # Save last section
    if current_section and current_text:
        sections.setdefault(current_section, []).append(" ".join(current_text))

    # Merge lists into single strings, truncate to ~8000 chars per section
    # （GLM-5.3-flash 上下文充裕，旧 4000 上限丢掉太多方法/实验细节）
    result = {}
    for name, texts in sections.items():
        combined = " ".join(texts)
        if len(combined) > 8000:
            combined = combined[:8000]
        if combined:
            result[name] = combined

    return result


def fetch_and_extract(arxiv_id: str) -> Optional[dict[str, str]]:
    """Fetch arXiv HTML and extract structured sections.

    Returns section dict or None if fetch/parse fails. ar5iv 对刚发布的论文
    尚未渲染时会返回平台占位页（仅数百字符的 arXivLabs 说明文字）——
    总字数过少视为抓取失败，返回 None 让该论文下轮重试。
    """
    html = fetch_arxiv_html(arxiv_id)
    if html is None:
        return None
    sections = extract_sections(html)
    if not sections:
        logger.warning(f"未能从 {arxiv_id} 提取任何章节")
        return None
    total_chars = sum(len(v) for v in sections.values())
    if total_chars < 2000:
        logger.warning(
            f"{arxiv_id} ar5iv 未渲染或返回占位页（{len(sections)} 节共 {total_chars} 字符），"
            f"跳过正文分析，待下轮重试"
        )
        return None
    logger.debug(f"Extracted {len(sections)} sections for {arxiv_id}: {list(sections.keys())}")
    return sections
