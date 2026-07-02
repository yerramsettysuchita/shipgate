# ShipGate demo recording script

A sixty second screen recording. Record it in one pass, then trim the two waiting
moments in editing. Speak slowly and let the screen do the work.

## Before you hit record
Stay signed in to lemma.work in this browser, so the app opens straight to the dashboard.
Open https://shipgate.apps.lemma.work and confirm the bottom right says build 8.
Confirm the coupon pull request is in the red and blocked, and the invoice one is shipped.
Close other tabs, set the browser zoom to a comfortable size, and hide bookmarks.
Have the fixed diff ready to paste. It is in the repo at seed/prA_fixed.json, copy only
the value of the diff field.

## The shots

Shot one, zero to ten seconds. The dashboard.
Show the whole dashboard. The queue on the left with two pull requests, the score badges,
the blocked and shipped counts at the top.
Say. Every tool reviews your code and leaves comments. None of them makes the call on
whether it is safe to ship. ShipGate does.

Shot two, ten to twenty eight seconds. The blocked pull request.
Click the coupon pull request. The detail opens. Point at the score in the red and the
red banner that says blocked by the gate. Scroll slowly through the risks. Read one out.
The migration with no rollback. The endpoint with no test. The description that promises
caching when the code has none. Click the Test plan tab for one second so they see it
exists.
Say. This one is blocked. The score is well below seventy and there is a critical risk.
And look at what it caught. A migration that cannot be undone, a new endpoint with no
test, and a claim in the description that the code never delivers. It even wrote the test
plan.

Shot three, twenty eight to thirty six seconds. Fix it and run again.
Click Edit diff. Paste the fixed diff over the old one. Click Save and evaluate. The score
badge starts spinning.
Say. Now we fix it. We add the rollback, a test, the changelog, and we make the
description honest. And we run the gate again.
Here you stop talking. In editing, cut out the wait while it evaluates.

Shot four, thirty six to fifty seconds. Approved with a certificate.
The screen now shows the score jumped into the nineties and the status is ready for sign
off. Click Approve for release. Add a short note if it asks. The status flips to approved.
Click the Sign off tab. Point at the certificate line.
Say. Now it passes, and a human approves it. The moment they do, ShipGate writes the
release notes and a signed certificate. That certificate is a hash of the exact decision,
so anyone can prove later what was approved and that nobody changed it.

Shot five, fifty to sixty seconds. It never stops watching.
Click Edit diff again. Paste the regressed diff from seed/prA_regressed.json. Save and
evaluate. In editing, cut the wait, then show the status flip to regressed.
Say. And it gates every release, not just the first. Push a bad migration on the next
commit and the same pull request flips straight to regressed. That is the whole idea.
Reviewing is not deciding. ShipGate owns the decision.

## If sixty seconds is too tight
It is fine to make it ninety seconds. The two evaluations each take a short moment because
the review agent is thorough. Either trim those moments in editing, or record the
regression part as a second short clip and place it at the end. Do not sign out of
lemma.work at any point during the recording, or the app will ask you to sign in again.
