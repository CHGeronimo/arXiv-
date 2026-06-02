from pydantic import BaseModel, Field, ConfigDict


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
    recommendation: str = Field(description="one of: must-read, recommended, reference, ignore")
    skip_reason: str = Field(default="", description='when recommendation is ignore: one of "low_relevance", "weak_method", "no_empirical", "domain_mismatch", "poor_quality"; otherwise empty string')


class QuickFilter(BaseModel):
    is_relevant: bool = Field(description="whether this paper is relevant to the user's research direction and worth detailed analysis")
    relevance_reason: str = Field(description="one sentence explaining why relevant or not")


class KnowledgeCard(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    problem: str = Field(description="the specific problem or research question this paper addresses, in one clear sentence", alias="Problem")
    method_extracted: str = Field(description="the core method, technique, or approach proposed, in one sentence", alias="Method")
    result_extracted: str = Field(description="the key result or finding, with metrics if available, in one sentence", alias="Result")
    keywords: list[str] = Field(description="5-10 technical keywords that characterize this paper's contribution and domain", alias="Keywords")
    relation_to_profile: str = Field(description="how this paper relates to the user's research direction: direct contribution, related technique, potential application, or tangential", alias="RelationToProfile")


class TrendReport(BaseModel):
    new_methods: str = Field(description="new methods or techniques that emerged this week, 2-4 items as bullet points")
    solved_problems: str = Field(description="problems that appear to have been addressed, 1-3 items")
    controversies: str = Field(description="debates or conflicting findings, if any")
    opportunities: str = Field(description="research opportunities or gaps visible from this week's papers")


class FulltextAnalysis(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method_implementation: str = Field(description="detailed description of how the method works: architecture, key algorithms, training procedure, design choices. 2-3 sentences", alias="MethodImplementation")
    experimental_design: str = Field(description="experimental setup: datasets, baselines, metrics, evaluation protocol, ablation studies. 2-3 sentences", alias="ExperimentalDesign")
    key_results_detail: str = Field(description="specific quantitative results: numbers, comparisons, state-of-the-art achievements. 2-3 sentences", alias="KeyResults")
    limitations: str = Field(description="stated or inferred limitations: assumptions, scalability issues, domain restrictions, negative results. 1-2 sentences", alias="Limitations")
    reproducibility: str = Field(description="reproducibility assessment: code available, hyperparameters specified, datasets accessible. 1 sentence", alias="Reproducibility")
    relevance_to_profile: str = Field(description="specific relevance to user's research: which techniques could transfer, what gaps this fills, potential collaborations. 1-2 sentences", alias="RelevanceToProfile")
