#input_type_name: RecordSignoffInput
#output_type_name: RecordSignoffResult
#function_name: record_signoff

import hashlib
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from lemma_sdk import FunctionContext, Pod


class RecordSignoffInput(BaseModel):
    pr_id: str
    decision: str            # "approved" | "changes_requested"
    approver: str
    note: Optional[str] = ""


class RecordSignoffResult(BaseModel):
    pr_id: str
    signoff_id: str
    decision: str
    status: str
    score_at_signoff: int
    open_criticals: int


async def record_signoff(ctx: FunctionContext, data: RecordSignoffInput) -> RecordSignoffResult:
    """Persist a human sign-off as an auditable record: who decided, when, at what
    score, with how many open criticals. Approve -> status=approved (release notes
    become final); request changes -> status=needs_fixes. This is the release gate's
    signed trail."""
    pod = Pod.from_env()
    pr = pod.table("pull_requests").get(data.pr_id)
    score = pr.get("readiness_score") or 0

    open_flags = pod.records.list("risk_flags", limit=500, filter=[
        {"field": "pr_id", "op": "eq", "value": data.pr_id},
        {"field": "status", "op": "eq", "value": "open"},
    ]).to_dict()["items"]
    open_criticals = sum(1 for f in open_flags if f.get("severity") == "critical")

    decision = "approved" if data.decision == "approved" else "changes_requested"
    now = datetime.now(timezone.utc).isoformat()

    # Tamper-evident certificate: a SHA-256 over the exact decision facts. Anyone
    # can recompute it from the recorded fields; if the score, approver, risks, or
    # time were altered after sign off, the hash no longer matches. This turns the
    # audit record into a verifiable release certificate.
    payload = "|".join([
        data.pr_id, decision, str(score), str(open_criticals),
        data.approver, now,
    ])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    certificate_id = "SG-" + digest[:20].upper()

    signoff = pod.table("sign_offs").create({
        "pr_id": data.pr_id,
        "decision": decision,
        "approver": data.approver,
        "note": data.note or "",
        "score_at_signoff": score,
        "open_criticals": open_criticals,
        "decided_at": now,
        "certificate_id": certificate_id,
    })

    new_status = "approved" if decision == "approved" else "needs_fixes"
    pod.table("pull_requests").update(data.pr_id, {"status": new_status})

    return RecordSignoffResult(
        pr_id=data.pr_id, signoff_id=str(signoff["id"]), decision=decision,
        status=new_status, score_at_signoff=score, open_criticals=open_criticals,
    )
