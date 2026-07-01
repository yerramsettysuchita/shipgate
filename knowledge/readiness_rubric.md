# Release-Readiness Rubric

The Release-Readiness Score is a deterministic, reproducible number from 0–100. It is
computed by the `compute_score` function — never guessed. This file explains the model
so the score can be defended line-by-line.

## Weighted dimensions (sum to 100)

| Dimension | Weight | Driven by |
|---|---|---|
| Correctness & broken-flow risk | 30 | open `correctness` risk flags |
| Test coverage of changed code  | 20 | `tests_for_new_code` check + agent test/edge flags (`tests`) |
| Migration safety               | 15 | `migration_reversible` check + `migration` risk flags |
| Breaking-change surface        | 15 | `breaking` risk flags |
| Docs & changelog freshness     | 12 | `docs_updated` + `changelog_updated` checks (`docs`) |
| Claim-vs-code integrity        | 8  | `claim_gap` risk flags |

## How the score is computed

1. Each dimension starts at its full weight.
2. Every **open** risk flag maps to a dimension by its `category`:
   - `correctness` → Correctness, `tests` → Test coverage, `migration` → Migration safety,
     `breaking` → Breaking-change surface, `docs` → Docs & changelog,
     `claim_gap` → Claim-vs-code, `security` → Correctness (and always critical).
3. Subtract a penalty from that dimension per open flag, by severity:
   - `critical` = 100% of the dimension weight
   - `serious`  = 60%
   - `moderate` = 30%
   - `minor`    = 10%
   Penalties are capped so a dimension never goes below 0.
4. Score = sum of remaining dimension points, rounded to an integer.
5. **Any open `critical` flag caps the total at 59 — an automatic block.**

## Failed deterministic checks become risk flags

When `run_checklist` records a `fail`, it also writes a matching `risk_flag` (source
`function`) so the failure is reflected in the score:

| Check | On fail → risk flag (category / severity) |
|---|---|
| `migration_reversible` | migration / critical |
| `tests_for_new_code`   | tests / serious |
| `changelog_updated`    | docs / minor |
| `docs_updated`         | docs / minor |
| `no_secrets`           | security / critical |
| `no_debug_leftovers`   | correctness / minor |
| `version_bumped`       | docs / minor |

The review agent adds `correctness`, `breaking`, and `claim_gap` flags (source `agent`)
that the checklist cannot detect.

## Gate

`gate_decision` returns **block** when the score is **< 70** OR any **open critical**
flag exists; otherwise **pass** (→ human sign-off). A block on a previously **approved**
PR is a **regression**.
