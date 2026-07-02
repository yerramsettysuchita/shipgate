# ShipGate

ShipGate is a release readiness gate for pull requests, built on Lemma.

Most tools that look at a pull request stop at leaving comments. ShipGate does the part they skip. It takes a PR, runs a set of deterministic checks and a review agent over it, gives the change a readiness score out of 100, and then either blocks it or hands it to a person to sign off. Once someone approves, it writes the release notes and a signed record of who approved it, when, at what score, and with which risks still open. When new commits land it runs again, so a change that passed before does not quietly regress.

The live app is at https://shipgate.apps.lemma.work

## Why I built this

Small teams ship fast and keep missing the same handful of things. A migration with no rollback path. A new endpoint that ships with no test. A description that claims one thing while the diff quietly does another. Docs and release notes that never get written.

The thing is, reviewing a diff is not the same as deciding it is safe to release. Plenty of tools read the diff and leave comments, but a pile of comments is not a decision. Nobody actually owns the go or no go call, so people merge on gut feel and afterwards there is no record of who approved what with which risks left open. ShipGate is my attempt to make that decision a real, owned, recorded step.

## How it works

Everything lives in one Lemma pod.

The tables hold the state. There is one for pull requests, one for the checklist results, one for risk flags, one for sign offs, and one for release notes. Every risk ShipGate finds becomes a row with a severity and the exact file and line it came from, so nothing is hand wavy.

The files under the knowledge folder are the agent's memory. One holds the scoring rubric, one holds the team's definition of done, and one holds the release notes template. They are plain markdown, so a team can edit what ready means and the gate follows along.

The functions are the deterministic core, and there is no model in them at all. parse_pr reads the diff and pulls out the changed files, the migrations, the new endpoints, the tests, and anything that looks like a secret or a leftover debug line. run_checklist runs the seven checks and writes a row for each one. compute_score turns the open risk flags into a number. gate_decision decides block or pass. Because this part is just code, the same diff always produces the same score, and you can defend it line by line.

The agent, called release-reviewer, does the judgment the checklist cannot. It compares what the PR claims against what the diff actually does and flags the gaps, for example a description that promises caching when there is no caching in the code. It looks for correctness and broken flow risks, and for breaking changes that would hurt existing callers. It writes each finding as a risk flag with real evidence, drafts a test plan for the edge cases the change introduces, and drafts the release notes.

The workflow, evaluate-and-gate, ties it together. It runs the checklist, scores and gates the PR first so the deterministic result always lands, then lets the agent add its findings and re scores. I put the deterministic gate before the agent on purpose, so that if the model has a bad moment the PR is still gated correctly instead of getting stuck.

The app is the dashboard where all of this is visible. You see the queue on the left with a score badge and status for each PR, and when you open one you get the score, the checklist with evidence, the risk flags, the test plan, and the release notes. When a PR passes, the Approve and Request changes buttons show up. When it is approved, you see the signed record and the final notes.

## The score

The score is spread across six weighted parts that add up to 100. Correctness carries 30, test coverage 20, migration safety 15, breaking change surface 15, docs and changelog 12, and claim versus code 8.

Each part starts at its full weight. Every open risk flag takes a bite out of its part depending on severity. A critical takes the whole thing, a serious takes most of it, and smaller ones take less. Any open critical caps the whole score at 59, which means it is an automatic block. A PR is ready for sign off when the score is at least 70 and there are no open criticals. Anything below that blocks and goes back for fixes. If a change that was already approved starts failing again, that is a regression and it gets called out.

## Running it yourself

You need the Lemma CLI and an account. Once you are logged in:

```
lemma pods create shipgate --description "Release readiness gate for pull requests."
lemma config set-default-pod shipgate
lemma pods import .
```

The file contents do not travel inside a bundle, so upload the three knowledge files after the import:

```
lemma files upload ./knowledge/readiness_rubric.md   /knowledge/readiness_rubric.md
lemma files upload ./knowledge/definition_of_done.md /knowledge/definition_of_done.md
lemma files upload ./knowledge/notes_template.md     /knowledge/notes_template.md
```

Then deploy the dashboard. The public slug is global, so pick another name if this one is taken:

```
lemma apps deploy shipgate ./app/index.html --yes
```

To land the demo data, run seed/seed.ps1. Records do not travel inside a bundle either, so this script creates the two example PRs, runs them through the gate, and approves the clean one.

## Trying the demo loop

Open the app. The coupon PR is blocked with its score in the red and a few risks called out, including a migration with no rollback, a new endpoint with no test, and a claim in the description that the diff never delivers. Open it and read the test plan.

Now hit Edit diff and paste the diff from seed/prA_fixed.json, which adds the rollback, a test, a changelog entry, docs, a version bump, and an honest description. Save and re evaluate, and the score jumps into the nineties and the PR moves to ready for sign off. Approve it, and the release notes finalize and the signed record appears.

Then paste seed/prA_regressed.json, which sneaks in an irreversible follow up migration, and re evaluate. The PR flips to regressed and the problem is flagged again. It gates every release, not just the first one.

## What is in and what is next

Right now it does the manual PR submit, the seven deterministic checks, the score, the agent findings and test plan and release notes, the approval gate, the signed record, the regression rerun, and the dashboard.

Things I would add next are a live GitHub webhook so it triggers itself, posting the result back onto the GitHub PR, indexing the whole codebase for deeper context, multi repo support, and approving straight from Slack.
