# Definition of Done

What "ready to release" means for this team. Editable — tune it and the gate follows.
Each item maps to a deterministic check in `run_checklist` and/or a judgment the review
agent makes.

## Required for every PR

1. **Tests for new code.** New source functions, endpoints, or files must ship with
   matching test changes. New behaviour without a test is not done.
2. **Migrations are reversible.** Any migration file must include a down / rollback path.
   A one-way migration is a critical release risk.
3. **Changelog updated on user-facing change.** Any change a user can observe requires a
   `CHANGELOG` entry.
4. **Docs updated on public API change.** Adding, removing, or changing a public
   endpoint / exported signature requires docs or README updates.
5. **Version bumped on release-affecting change.** Public/user-facing changes bump the
   version (or add a changeset).
6. **No secrets or PII.** Added lines must not contain API keys, tokens, passwords,
   private keys, or personal data. This is a hard block.
7. **No debug leftovers.** No stray `console.log`, `print` debug lines, `TODO`/`FIXME`
   left in changed code.

## Judgment items (review agent)

- **Claim-vs-code integrity.** The PR description must match what the diff actually does.
  If the description claims a behaviour (e.g. "adds retry with backoff", "adds caching")
  that is not present in the diff, that is a `claim_gap`.
- **Correctness & broken flows.** Logic in the diff that can break an existing flow —
  each with concrete file + hunk evidence.
- **Breaking changes.** Signature or behaviour changes that affect existing callers.

## Ready bar

A PR is **ready for sign-off** when the readiness score is **≥ 70** and there are **no
open critical flags**. Below that, the gate blocks and the PR returns for fixes.
