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
