#input_type_name: RunChecklistInput
#output_type_name: RunChecklistResult
#function_name: run_checklist

import re
from typing import List, Optional
from pydantic import BaseModel
from lemma_sdk import FunctionContext, Pod


# ---------------------------------------------------------------------------
# Same deterministic diff parser as parse_pr (kept in sync; functions are
# sandboxed and cannot import one another).
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"ghp_[0-9A-Za-z]{36}", "GitHub token"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "Slack token"),
    (r"(?i)(api[_-]?key|secret|password|passwd|access[_-]?token|auth[_-]?token)\s*[:=]\s*['\"][^'\"]{6,}['\"]", "hardcoded credential"),
    (r"(?i)aws_secret_access_key\s*[:=]", "AWS secret access key"),
]
DEBUG_PATTERNS = [
    (r"console\.log\s*\(", "console.log"),
    (r"\bdebugger\b", "debugger statement"),
    (r"pdb\.set_trace\s*\(", "pdb.set_trace"),
    (r"binding\.pry", "binding.pry"),
    (r"\bprint\s*\(", "print() debug"),
    (r"(?i)\b(TODO|FIXME)\b", "TODO/FIXME"),
]
ENDPOINT_PATTERNS = [
    r"@(?:app|router|blueprint|bp)\.(?:route|get|post|put|delete|patch)\s*\(",
    r"\b(?:app|router)\.(?:get|post|put|delete|patch)\s*\(",
    r"@(?:Get|Post|Put|Delete|Patch)Mapping",
]
CODE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rb", ".rs",
            ".c", ".cc", ".cpp", ".php", ".kt", ".scala", ".cs")


def _is_test(p): return bool(re.search(r"(^|/)(tests?|__tests__|spec)/|(_test|\.test|\.spec|_spec)\.|(^|/)test_[^/]+$", p, re.I))
def _is_migration(p): return bool(re.search(r"(^|/)migrations?/|(^|/)alembic/|\.migration", p, re.I))
def _is_changelog(p): return bool(re.search(r"changelog", p, re.I))
def _is_docs(p): return bool(re.search(r"(^|/)docs?/|readme", p, re.I) or p.lower().endswith(".md"))


def _is_version(p):
    base = p.rsplit("/", 1)[-1].lower()
    return base in ("package.json", "pyproject.toml", "setup.py", "setup.cfg",
                    "version", "version.txt", "version.py", "__version__.py", "cargo.toml")


def _is_source(p):
    return p.lower().endswith(CODE_EXT) and not _is_test(p) and not _is_migration(p)


def parse_diff(title: str, description: str, diff: str) -> dict:
    diff = diff or ""
    changed_files, added, removed, added_lines, cur, per_file_added = [], 0, 0, [], None, {}
    for raw in diff.splitlines():
        m = re.match(r"^diff --git a/(.+?) b/(.+)$", raw)
        if m:
            cur = m.group(2).strip()
            if cur not in changed_files:
                changed_files.append(cur); per_file_added[cur] = []
            continue
        m = re.match(r"^\+\+\+ b/(.+)$", raw)
        if m:
            cur = m.group(1).strip()
            if cur != "/dev/null" and cur not in changed_files:
                changed_files.append(cur); per_file_added.setdefault(cur, [])
            continue
        if raw.startswith("--- "):
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            added += 1; line = raw[1:]; added_lines.append(line)
            if cur is not None:
                per_file_added.setdefault(cur, []).append(line)
        elif raw.startswith("-") and not raw.startswith("---"):
            removed += 1

    migration_files = [f for f in changed_files if _is_migration(f)]
    test_files = [f for f in changed_files if _is_test(f)]
    changelog_files = [f for f in changed_files if _is_changelog(f)]
    version_files = [f for f in changed_files if _is_version(f)]
    docs_files = [f for f in changed_files if _is_docs(f)]
    source_files = [f for f in changed_files if _is_source(f)]

    new_endpoints = []
    for f in changed_files:
        for ln in per_file_added.get(f, []):
            if any(re.search(p, ln) for p in ENDPOINT_PATTERNS):
                new_endpoints.append(f"{f}: {ln.strip()[:120]}")

    migration_has_down = False
    for f in migration_files:
        blob = "\n".join(per_file_added.get(f, []))
        if re.search(r"\b(downgrade|rollback)\b|def\s+down\b|\bdown\s*\(|--\s*down|down\s*=", blob, re.I):
            migration_has_down = True
            break

    secrets_found = []
    for ln in added_lines:
        for pat, label in SECRET_PATTERNS:
            if re.search(pat, ln):
                secrets_found.append(f"{label}: {ln.strip()[:60]}"); break

    debug_leftovers = []
    for ln in added_lines:
        for pat, label in DEBUG_PATTERNS:
            if re.search(pat, ln):
                debug_leftovers.append(f"{label}: {ln.strip()[:80]}"); break

    has_source_change = len(source_files) > 0 or len(new_endpoints) > 0
    has_new_source_code = any(
        re.search(r"\bdef\s+\w+\s*\(|\bfunction\s+\w+\s*\(|\bfunc\s+\w+\s*\(|=>\s*\{|\bclass\s+\w+", ln)
        for f in source_files for ln in per_file_added.get(f, [])
    ) or len(new_endpoints) > 0

    return {
        "changed_files": changed_files, "added_lines": added, "removed_lines": removed,
        "migration_files": migration_files, "test_files": test_files,
        "changelog_files": changelog_files, "version_files": version_files,
        "docs_files": docs_files, "source_files": source_files,
        "new_endpoints": new_endpoints[:10], "migration_has_down": migration_has_down,
        "secrets_found": secrets_found[:10], "debug_leftovers": debug_leftovers[:10],
        "has_source_change": has_source_change, "has_new_source_code": has_new_source_code,
    }


class RunChecklistInput(BaseModel):
    pr_id: str


class CheckRow(BaseModel):
    check_key: str
    label: str
    result: str
    evidence: str


class RunChecklistResult(BaseModel):
    pr_id: str
    checks: List[CheckRow]
    fails: int
    flags_written: int


async def run_checklist(ctx: FunctionContext, data: RunChecklistInput) -> RunChecklistResult:
    """Run the 7 deterministic definition-of-done checks and write one
    checklist_results row per check. Every fail also becomes a function-source
    risk_flag so the score reflects it. Idempotent: clears prior checklist rows
    and open flags for this PR first."""
    pod = Pod.from_env()
    pr = pod.table("pull_requests").get(data.pr_id)

    # mark evaluating
    pod.table("pull_requests").update(data.pr_id, {"status": "evaluating"})

    parsed = parse_diff(pr.get("title", ""), pr.get("description", ""), pr.get("diff", ""))

    # --- idempotency: clear prior checklist rows + all flags for this PR ---
    old_checks = pod.records.list("checklist_results", limit=200,
        filter=[{"field": "pr_id", "op": "eq", "value": data.pr_id}]).to_dict()["items"]
    if old_checks:
        pod.records.bulk_delete("checklist_results", [r["id"] for r in old_checks])
    old_flags = pod.records.list("risk_flags", limit=200,
        filter=[{"field": "pr_id", "op": "eq", "value": data.pr_id}]).to_dict()["items"]
    if old_flags:
        pod.records.bulk_delete("risk_flags", [r["id"] for r in old_flags])

    checks: List[dict] = []
    flags: List[dict] = []

    def add(check_key, label, result, evidence, weight,
            flag_cat: Optional[str] = None, flag_sev: Optional[str] = None,
            flag_desc: Optional[str] = None):
        checks.append({"pr_id": data.pr_id, "check_key": check_key, "label": label,
                       "result": result, "evidence": evidence, "weight": weight})
        if result == "fail" and flag_cat:
            flags.append({"pr_id": data.pr_id, "category": flag_cat, "severity": flag_sev,
                          "description": flag_desc or label, "evidence": evidence,
                          "source": "function", "status": "open"})

    # 1. migration_reversible
    if not parsed["migration_files"]:
        add("migration_reversible", "Migrations are reversible", "na",
            "No migration files in this PR.", 15)
    elif parsed["migration_has_down"]:
        add("migration_reversible", "Migrations are reversible", "pass",
            "Down/rollback path found in " + ", ".join(parsed["migration_files"]) + ".", 15)
    else:
        add("migration_reversible", "Migrations are reversible", "fail",
            "Migration " + ", ".join(parsed["migration_files"]) + " has no down/rollback path.", 15,
            "migration", "critical",
            "One-way migration: " + ", ".join(parsed["migration_files"]) + " has no down/rollback path.")

    # 2. tests_for_new_code
    if not parsed["has_new_source_code"]:
        add("tests_for_new_code", "Tests for new code", "na",
            "No new source functions/endpoints detected.", 20)
    elif parsed["test_files"]:
        add("tests_for_new_code", "Tests for new code", "pass",
            "Test changes present: " + ", ".join(parsed["test_files"]) + ".", 20)
    else:
        ev = "New code (" + ", ".join(parsed["source_files"][:3] + parsed["new_endpoints"][:2]) + ") with no matching test changes."
        add("tests_for_new_code", "Tests for new code", "fail", ev, 20,
            "tests", "serious", ev)

    # 3. changelog_updated
    if not parsed["has_source_change"]:
        add("changelog_updated", "Changelog updated on user-facing change", "na",
            "No user-facing source change.", 6)
    elif parsed["changelog_files"]:
        add("changelog_updated", "Changelog updated on user-facing change", "pass",
            "CHANGELOG touched: " + ", ".join(parsed["changelog_files"]) + ".", 6)
    else:
        add("changelog_updated", "Changelog updated on user-facing change", "fail",
            "User-facing change with no CHANGELOG entry.", 6,
            "docs", "minor", "User-facing change with no CHANGELOG entry.")

    # 4. docs_updated
    if not parsed["new_endpoints"]:
        add("docs_updated", "Docs updated on public API change", "na",
            "No public API/endpoint change.", 6)
    elif parsed["docs_files"]:
        add("docs_updated", "Docs updated on public API change", "pass",
            "Docs touched: " + ", ".join(parsed["docs_files"]) + ".", 6)
    else:
        ev = "New endpoint(s) " + "; ".join(parsed["new_endpoints"][:2]) + " with no docs/README update."
        add("docs_updated", "Docs updated on public API change", "fail", ev, 6,
            "docs", "minor", ev)

    # 5. version_bumped
    if not parsed["has_source_change"]:
        add("version_bumped", "Version bumped on release-affecting change", "na",
            "No release-affecting change.", 0)
    elif parsed["version_files"]:
        add("version_bumped", "Version bumped on release-affecting change", "pass",
            "Version file touched: " + ", ".join(parsed["version_files"]) + ".", 0)
    else:
        add("version_bumped", "Version bumped on release-affecting change", "fail",
            "Release-affecting change with no version bump.", 0,
            "docs", "minor", "Release-affecting change with no version bump.")

    # 6. no_secrets
    if parsed["secrets_found"]:
        add("no_secrets", "No secrets or PII", "fail",
            "; ".join(parsed["secrets_found"][:3]), 100,
            "security", "critical", "Secret/credential-like pattern in added lines: " + "; ".join(parsed["secrets_found"][:3]))
    else:
        add("no_secrets", "No secrets or PII", "pass",
            "No secret/PII-like patterns in added lines.", 100)

    # 7. no_debug_leftovers
    if parsed["debug_leftovers"]:
        add("no_debug_leftovers", "No debug leftovers", "fail",
            "; ".join(parsed["debug_leftovers"][:3]), 2,
            "correctness", "minor", "Debug leftovers in added lines: " + "; ".join(parsed["debug_leftovers"][:3]))
    else:
        add("no_debug_leftovers", "No debug leftovers", "pass",
            "No TODO/FIXME/console.log/print debug in added lines.", 2)

    pod.records.bulk_create("checklist_results", checks)
    if flags:
        pod.records.bulk_create("risk_flags", flags)

    fails = sum(1 for c in checks if c["result"] == "fail")
    return RunChecklistResult(
        pr_id=data.pr_id,
        checks=[CheckRow(**{k: c[k] for k in ("check_key", "label", "result", "evidence")}) for c in checks],
        fails=fails,
        flags_written=len(flags),
    )
