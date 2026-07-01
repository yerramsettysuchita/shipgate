# ShipGate — release-readiness gate for pull requests

Every AI tool reviews code and leaves comments. **None of them makes the release
decision.** ShipGate does: a PR is submitted, evaluated by deterministic checks plus a
review agent, scored **0–100**, and either **blocked** or sent to a **human sign-off**.
On approval it generates release notes and writes a **signed audit record**, and it
**re-runs on new commits to catch regressions**.

Built on Lemma. Live app: **https://shipgate.apps.lemma.work**

---

## Architecture (Lemma primitives)

| Layer | Resource | Role |
|---|---|---|
| **Tables** | `pull_requests`, `checklist_results`, `risk_flags`, `sign_offs`, `release_notes` | All state. Every risk is a tracked row with severity + exact evidence. |
| **Files** (`/knowledge`) | `readiness_rubric.md`, `definition_of_done.md`, `notes_template.md` | Agent memory: the scoring model + the team's editable definition-of-done. |
| **Functions** (deterministic, no LLM) | `parse_pr`, `run_checklist`, `compute_score`, `gate_decision` | The defensible core: parse the diff, run the 7 checks, compute the reproducible score, gate. |
| | `evaluate_pr`, `record_signoff` | Orchestration: start the workflow; persist a human sign-off as an audit record. |
| **Agent** | `release-reviewer` | Judgment the checklist can't do: claim-vs-code gaps, correctness/broken-flow risks, breaking changes, a test plan, and a release-notes draft. |
| **Workflow** | `evaluate-and-gate` | `checklist → score → gate (deterministic) → agent → re-score → re-gate`. The deterministic gate runs **first**, so a PR is always gated even if the agent step hiccups. |
| **App** | `shipgate` (single-file HTML) | The readiness dashboard: queue, score gauge, checklist, risk flags, test plan, notes, the Approve/Request-changes gate, and the signed audit record. |

### The Release-Readiness Score (hero feature)

Six weighted dimensions summing to 100 — correctness 30, test coverage 20, migration
safety 15, breaking-change surface 15, docs/changelog 12, claim-vs-code 8. Each dimension
starts full; every **open** risk flag subtracts a severity-scaled penalty (critical 100%,
serious 60%, moderate 30%, minor 10%, capped at the dimension weight). **Any open critical
caps the total at 59 (auto-block).** Deterministic and reproducible — defensible
line-by-line. Full model in `knowledge/readiness_rubric.md`.

**Gate:** block if score < 70 **or** any open critical. A block on a previously-approved
PR is a **regression**.

---

## Setup from scratch (rebuild this pod)

```bash
# 0. tooling + auth (once)
uv tool install lemma-terminal
lemma servers cloud --use
lemma auth login
lemma skills install

# 1. create the pod and import the bundle (tables → files → functions → agent → workflow)
lemma pods create shipgate --description "Release-readiness gate for pull requests."
lemma config set-default-pod shipgate
lemma pods import .

# 2. upload the agent-memory files (file CONTENTS do not travel in bundles)
lemma files upload ./knowledge/readiness_rubric.md   /knowledge/readiness_rubric.md
lemma files upload ./knowledge/definition_of_done.md /knowledge/definition_of_done.md
lemma files upload ./knowledge/notes_template.md     /knowledge/notes_template.md

# 3. deploy the dashboard (public slug is global; change if taken)
lemma apps deploy shipgate ./app/index.html --yes

# 4. seed the demo (see seed/seed.ps1)
```

> **Grants note (zero-access by default).** `evaluate_pr` holds `workflow.read` +
> `workflow.execute` on `evaluate-and-gate`; `run_checklist` writes `checklist_results`
> and `risk_flags`; the agent writes `risk_flags`, `release_notes`, and only the
> `test_plan` field of `pull_requests`; `record_signoff` writes `sign_offs`. All in the
> bundle JSON, replaced on import.

---

## Verify (smoke test)

```bash
# deterministic core on a pasted diff:
lemma functions run parse_pr --file ./payloads/sample_pr.json

# full pipeline on the seeded blocked PR:
lemma workflows run evaluate-and-gate --file ./payloads/pr1_id.json
lemma query run "select title, status, readiness_score from pull_requests"
lemma records list risk_flags --limit 10
```

Expected for the blocked coupon PR: **needs_fixes**, score ≈ 59, open flags including a
critical `migration` (no down-path), a serious `tests` (no test), and a serious
`claim_gap` (description promises caching/retry that the diff doesn't contain).

---

## Demo loop (block → fix → approve → regress)

1. Open the app. The **coupon PR** is `needs_fixes` — score in the red, three evidenced
   risks, the gate blocking. Show the auto-generated test plan.
2. **Edit diff** → paste `seed/prA_fixed.json`'s diff (adds a down-migration, a test,
   changelog/docs/version, honest description) → **Save & re-evaluate** → score jumps to
   the 90s, `ready_for_signoff`.
3. **Approve for release** → sign-off recorded, release notes final, **signed audit
   record** shown (approver, time, score at sign-off, open criticals).
4. **Edit diff** → paste `seed/prA_regressed.json`'s diff (irreversible follow-up
   migration) → re-evaluate → **regressed**, flagged. "It gates every release, not just
   the first."

---

## MVP cut line

**Ships:** manual PR submit, 7 deterministic checks, the score, agent claim-vs-code +
risk flags + test plan + release notes, the approval gate, the signed record, regression
re-run, the dashboard.

**Deferred (roadmap):** live GitHub webhook auto-trigger, posting results back to the
GitHub PR, full-codebase indexing, multi-repo, approve-from-Slack.
