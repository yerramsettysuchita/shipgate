#input_type_name: ComputeScoreInput
#output_type_name: ComputeScoreResult
#function_name: compute_score

from typing import Dict, List
from pydantic import BaseModel
from lemma_sdk import FunctionContext, Pod

# Weighted dimensions summing to 100 (see /knowledge/readiness_rubric.md).
DIMENSIONS = {
    "correctness": 30,
    "tests": 20,
    "migration": 15,
    "breaking": 15,
    "docs": 12,
    "claim_gap": 8,
}
# Map each risk_flag category to a scored dimension.
CATEGORY_TO_DIM = {
    "correctness": "correctness",
    "tests": "tests",
    "migration": "migration",
    "breaking": "breaking",
    "docs": "docs",
    "claim_gap": "claim_gap",
    "security": "correctness",  # security has no dimension of its own; always critical -> caps total
}
SEVERITY_PCT = {"critical": 1.0, "serious": 0.6, "moderate": 0.3, "minor": 0.1}
CRITICAL_CAP = 59


class ComputeScoreInput(BaseModel):
    pr_id: str


class DimensionBreakdown(BaseModel):
    dimension: str
    weight: int
    remaining: float
    penalties: float


class ComputeScoreResult(BaseModel):
    pr_id: str
    score: int
    open_criticals: int
    capped_by_critical: bool
    dimensions: List[DimensionBreakdown]


async def compute_score(ctx: FunctionContext, data: ComputeScoreInput) -> ComputeScoreResult:
    """Deterministic, reproducible 0-100 readiness score from the PR's OPEN
    risk flags. Every dimension starts at full weight; each open flag subtracts
    a severity-scaled penalty (capped at the dimension weight). Any open
    critical caps the total at 59 (auto-block). Writes readiness_score."""
    pod = Pod.from_env()

    flags = pod.records.list("risk_flags", limit=500, filter=[
        {"field": "pr_id", "op": "eq", "value": data.pr_id},
        {"field": "status", "op": "eq", "value": "open"},
    ]).to_dict()["items"]

    remaining: Dict[str, float] = {d: float(w) for d, w in DIMENSIONS.items()}
    penalties: Dict[str, float] = {d: 0.0 for d in DIMENSIONS}
    open_criticals = 0

    for f in flags:
        cat = f.get("category")
        sev = f.get("severity")
        if sev == "critical":
            open_criticals += 1
        dim = CATEGORY_TO_DIM.get(cat)
        if not dim:
            continue
        weight = DIMENSIONS[dim]
        penalty = weight * SEVERITY_PCT.get(sev, 0.0)
        applied = min(penalty, remaining[dim])
        remaining[dim] -= applied
        penalties[dim] += applied

    score = round(sum(remaining.values()))
    capped = open_criticals > 0
    if capped:
        score = min(score, CRITICAL_CAP)
    score = max(0, min(100, score))

    pod.table("pull_requests").update(data.pr_id, {"readiness_score": score})

    return ComputeScoreResult(
        pr_id=data.pr_id,
        score=score,
        open_criticals=open_criticals,
        capped_by_critical=capped,
        dimensions=[
            DimensionBreakdown(dimension=d, weight=DIMENSIONS[d],
                               remaining=round(remaining[d], 1), penalties=round(penalties[d], 1))
            for d in DIMENSIONS
        ],
    )
