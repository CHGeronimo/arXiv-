from pydantic import BaseModel, Field


class Structure(BaseModel):
    tldr: str = Field(description="one-sentence TL;DR summary of the paper's key contribution")
    motivation: str = Field(description="what problem does this paper address and why it matters")
    method: str = Field(description="the proposed approach or methodology")
    result: str = Field(description="key experimental results and metrics")
    conclusion: str = Field(description="main takeaways and significance")
    title_zh: str = Field(description="Chinese translation of the paper title")
    summary_zh: str = Field(description="Chinese translation of the paper abstract")
    quality_score: int = Field(description="paper quality score from 1-10: 1=trivial/incremental, 5=solid contribution, 10=breakthrough work")
    relevance_score: int = Field(description="relevance to user research direction from 1-10: 1=unrelated, 5=tangentially related, 10=directly addresses core topic")
    recommendation: str = Field(description="one of: must-read, worth-reading, skim, skip")
    skip_reason: str = Field(default="", description="when skip: one sentence why; otherwise empty string")


class QuickFilter(BaseModel):
    is_relevant: bool = Field(description="whether this paper is relevant to the user's research direction and worth detailed analysis")
    relevance_reason: str = Field(description="one sentence explaining why relevant or not")


class KnowledgeCard(BaseModel):
    problem: str = Field(description="the specific problem or research question this paper addresses, in one clear sentence")
    method_extracted: str = Field(description="the core method, technique, or approach proposed, in one sentence")
    result_extracted: str = Field(description="the key result or finding, with metrics if available, in one sentence")
    keywords: list[str] = Field(description="5-10 technical keywords that characterize this paper's contribution and domain")
    relation_to_profile: str = Field(description="how this paper relates to the user's research direction: direct contribution, related technique, potential application, or tangential")
