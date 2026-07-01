#input_type_name: EvaluatePrInput
#output_type_name: EvaluatePrResult
#function_name: evaluate_pr

from pydantic import BaseModel
from lemma_sdk import FunctionContext, Pod


class EvaluatePrInput(BaseModel):
    pr_id: str


class EvaluatePrResult(BaseModel):
    pr_id: str
    run_id: str
    status: str


async def evaluate_pr(ctx: FunctionContext, data: EvaluatePrInput) -> EvaluatePrResult:
    """Start the evaluate-and-gate workflow for a PR and submit its intake form.
    Called by the dashboard app to (re-)evaluate a PR. JOB type so the ~60s agent
    step never hits a request timeout; the app polls pull_requests for the result."""
    pod = Pod.from_env()

    # mark as evaluating immediately so the UI reflects it before the workflow starts
    pod.table("pull_requests").update(data.pr_id, {"status": "evaluating"})

    run = pod.workflows.create_run("evaluate-and-gate")
    run_id = str(run.id)

    # Submit the intake form. The server accepts it and continues the workflow
    # (checklist -> agent -> score -> gate) asynchronously, returning promptly; the
    # app polls pull_requests for the result.
    status = str(run.status)
    if run.active_wait and run.active_wait.wait_type == "HUMAN":
        submitted = pod.workflows.submit_form(
            run_id, node_id=run.active_wait.node_id, inputs={"pr_id": data.pr_id}
        )
        status = str(submitted.status)

    return EvaluatePrResult(pr_id=data.pr_id, run_id=run_id, status=status)
