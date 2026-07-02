# ShipGate pitch deck

Slide by slide content with speaker notes. Written to drop straight into PowerPoint or
Google Slides. Keep one idea per slide. The words under On the slide go on the slide.
The words under What to say are for you to speak, not to print.

Live app https://shipgate.apps.lemma.work
Repo https://github.com/yerramsettysuchita/shipgate


## Slide 1. Title

On the slide
ShipGate
The release readiness gate for pull requests
Built on Lemma
Your name and your teammate name

What to say
Hi, we are Suchita and Manjunath. We built ShipGate. Most tools review your code and
leave comments. ShipGate does the thing none of them do. It makes the call on whether a
change is actually safe to ship, and it keeps a signed record of that decision.


## Slide 2. The problem

On the slide
Small teams ship fast and keep missing the same handful of things
A migration with no rollback path
A new endpoint that ships with no test
A description that claims one thing while the code does another
Docs and release notes that never get written

What to say
Every fast moving team has felt this. You merge on a Friday and on Monday something is
broken that everyone could have caught. A migration that cannot be undone. An endpoint
with no test. A pull request that says it adds caching when it never did.


## Slide 3. The gap nobody fills

On the slide
Reviewing a diff is not the same as deciding it is safe to release
The market is full of tools that read the diff and leave comments
A pile of comments is not a decision
Nobody owns the go or no go call, and there is no record of who approved what

What to say
There are plenty of AI reviewers now. They all do the same thing. They comment on the
diff. But a comment is not a decision. No tool actually owns the moment where a person
says yes, ship it, and stands behind it. So teams merge on gut feel and there is no
trail of who approved what with which risks still open.


## Slide 4. What ShipGate does

On the slide
ShipGate turns a pull request into an owned and recorded go or no go decision
It scores the change from 0 to 100
It blocks the change or sends it to a person to sign off
On approval it writes the release notes and a signed certificate
It runs again on new commits to catch regressions

What to say
ShipGate is the missing step. A pull request comes in. We score it, we gate it, a human
signs off, and we keep a signed record of exactly what was approved and with what risks
were still open. Then we do it all again on the next commit.


## Slide 5. How it works

On the slide
Deterministic checks run first, plain code, no model, fully reproducible
The review agent then adds the judgment the checks cannot make
The score and the gate decide block or ready for sign off
A person approves and the certificate is written
On a new commit it all runs again

What to say
The flow has two halves. First the deterministic half, plain Python that parses the diff
and runs seven checks. Then the judgment half, an agent that compares what the
description claims against what the code actually does. The score comes from both, the
gate decides, and a human makes the final call.


## Slide 6. The readiness score

On the slide
Six weighted parts add up to 100
Correctness 30, test coverage 20, migration safety 15, breaking change 15, docs and
changelog 12, claim versus code 8
Every open risk takes a slice out of its part based on severity
Any open critical caps the whole score at 59, which is an automatic block

What to say
The score is not a vibe. It is arithmetic over evidence. Every dimension starts full,
every open risk subtracts a known amount, and any critical caps the whole thing at 59.
The same diff always gives the same score. We can defend the number line by line, which
is the one thing a vibe reviewer can never do.


## Slide 7. The review agent

On the slide
Claim versus code, the description promises caching and the diff has none
Correctness risks, an endpoint that never saves, a value with no range check
Breaking changes that would hurt existing callers
Every finding is a tracked row with a severity and the exact file and line

What to say
On our demo pull request the agent caught the claim gap, caching was promised but never
written. Then it caught two real bugs, no handling for a duplicate coupon and no range
check on the percent. These are exactly the things a tired reviewer misses on a Friday
evening.


## Slide 8. The human gate and the signed certificate

On the slide
Below 70 or any open critical, the gate blocks
Otherwise a person clicks Approve for release or Request changes
On approval ShipGate writes a tamper evident certificate
A SHA 256 taken over the pull request, the score, the open risks, the approver and the time

What to say
This is the part no other tool has. When someone approves, we hash the exact facts of
the decision. Anyone can recompute that hash from the record. If the score or the
approver or the risks were changed after the fact, the certificate no longer matches.
Every release ships with proof of what was approved.


## Slide 9. It gates every release, not just the first

On the slide
A change that was already approved can regress on the very next commit
ShipGate runs again, detects it, and flags the release as regressed

What to say
Approval is not forever. If a later commit brings back a risk that was already cleared,
ShipGate catches it and marks the release regressed. It gates every ship, not only the
first one.


## Slide 10. Built on Lemma

On the slide
Tables hold every record, the pull requests, the checks, the risks, the sign offs and the notes
Files hold the scoring rubric and the team definition of done
Functions run the deterministic checks and compute the score
An agent does the judgment work
A workflow ties it together with a real human approval step
An app is the dashboard the whole team lives in

What to say
Lemma is the entire backend. We did not bolt a database onto a script. Tables, files,
functions, an agent, a workflow with a genuine human step, and the app. The human
approval step inside the workflow is the thing that made this whole product possible.


## Slide 11. Demo

On the slide
Block, fix, approve, regress
A screenshot of the dashboard on the blocked pull request

What to say
Here is the loop. A blocked pull request with the score in the red and real risks with
evidence. We fix the diff and run it again, the score jumps and it moves to ready for
sign off. A person approves and the certificate is written. Then we sneak a bad
migration back in, run it again, and it regresses.


## Slide 12. Why we win

On the slide
Every competitor reviews code. We own the release decision.
The score is reproducible and defensible
The record is signed and verifiable
It gates every commit, not only the first

What to say
The whole field competes on catching bugs. We chose not to. We compete on the decision.
A reproducible score, a signed and verifiable record, and a gate that never stops
watching. That is a category of one.


## Slide 13. Roadmap and links

On the slide
Next, a GitHub webhook so it triggers itself on every push
Post the result back onto the GitHub pull request
Approve straight from Slack
Live app https://shipgate.apps.lemma.work
Repo https://github.com/yerramsettysuchita/shipgate

What to say
Next we wire it straight into GitHub so it triggers on every push and posts the result
back onto the pull request, and we add approve from Slack. The app is live and the code
is public. Thank you.
