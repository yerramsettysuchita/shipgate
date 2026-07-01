# ShipGate demo seed — run after `lemma pods import .` and the file uploads.
# Records + file contents do NOT travel in a bundle; this lands the demo state.
# Usage:  pwsh -File seed/seed.ps1
$ErrorActionPreference = "Stop"

function PrId($json) { ($json | ConvertFrom-Json).id }

Write-Host "Creating blocked hero PR (acme/checkout #482)..."
$a = lemma --output json records create pull_requests --file ./seed/prA_blocked.json | Out-String
$aid = PrId $a
"{`"pr_id`":`"$aid`"}" | Out-File -Encoding ascii ./payloads/pr1_id.json
lemma workflows run evaluate-and-gate --data (@{pr_id=$aid} | ConvertTo-Json -Compress) | Out-Null   # -> needs_fixes

Write-Host "Creating clean PR (acme/billing #517) and approving it..."
$b = lemma --output json records create pull_requests --file ./seed/prB_clean.json | Out-String
$bid = PrId $b
lemma workflows run evaluate-and-gate --data (@{pr_id=$bid} | ConvertTo-Json -Compress) | Out-Null   # -> ready_for_signoff
lemma functions run record_signoff --data (@{pr_id=$bid; decision="approved"; approver="priya@acme.dev"; note="Clean fix with a regression test. Cleared for 2.1.4."} | ConvertTo-Json -Compress) | Out-Null

Write-Host "Seeded. Open the dashboard:  https://shipgate.apps.lemma.work"
Write-Host "Demo diffs for the live loop: seed/prA_fixed.json (fix) and seed/prA_regressed.json (regress)."
