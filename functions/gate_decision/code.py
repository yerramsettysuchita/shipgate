#input_type_name: GateDecisionInput
#output_type_name: GateDecisionResult
#function_name: gate_decision

from pydantic import BaseModel
from lemma_sdk import FunctionContext, Pod

SCORE_THRESHOLD = 70


class GateDecisionInput(BaseModel):
    pr_id: str


class GateDecisionResult(BaseModel):
    pr_id: str
    decision: str          # "block" | "pass"
    status: str            # resulting pull_requests status
    score: int
    open_criticals: int
    previously_approved: bool
    reason: str


async def gate_decision(ctx: FunctionContext, data: GateDecisionInput) -> GateDecisionResult:
    """Gate: block if score < 70 OR any open critical flag; else pass to human
    sign-off. A block on a previously-approved PR is a regression. Sets the
    resulting pull_requests status."""
    pod = Pod.from_env()
    pr = pod.table("pull_requests").get(data.pr_id)
    score = pr.get("readiness_score") or 0

    open_flags = pod.records.list("risk_flags", limit=500, filter=[
        {"field": "pr_id", "op": "eq", "value": data.pr_id},
        {"field": "status", "op": "eq", "value": "open"},
    ]).to_dict()["items"]
    open_criticals = sum(1 for f in open_flags if f.get("severity") == "critical")

    prior_approvals = pod.records.list("sign_offs", limit=50, filter=[
        {"field": "pr_id", "op": "eq", "value": data.pr_id},
        {"field": "decision", "op": "eq", "value": "approved"},
    ]).to_dict()["items"]
    previously_approved = len(prior_approvals) > 0

    block = score < SCORE_THRESHOLD or open_criticals > 0
    if block:
        decision = "block"
        status = "regressed" if previously_approved else "needs_fixes"
        bits = []
        if score < SCORE_THRESHOLD:
            bits.append(f"score {score} < {SCORE_THRESHOLD}")
        if open_criticals > 0:
            bits.append(f"{open_criticals} open critical risk(s)")
        reason = ("Regression: " if previously_approved else "Blocked: ") + " and ".join(bits) + "."
    else:
        decision = "pass"
        status = "ready_for_signoff"
        reason = f"Passed gate: score {score} >= {SCORE_THRESHOLD}, no open criticals. Ready for human sign-off."

    pod.table("pull_requests").update(data.pr_id, {"status": status})

    return GateDecisionResult(
        pr_id=data.pr_id, decision=decision, status=status, score=score,
        open_criticals=open_criticals, previously_approved=previously_approved, reason=reason,
    )
