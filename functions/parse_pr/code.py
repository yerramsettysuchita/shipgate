#input_type_name: ParsePrInput
#output_type_name: ParsePrResult
#function_name: parse_pr

import re
from typing import List
from pydantic import BaseModel
from lemma_sdk import FunctionContext, Pod


# ---------------------------------------------------------------------------
# Deterministic diff parsing. Pure, reproducible, no LLM. This same helper is
# embedded in run_checklist so the checklist and this standalone parser agree.
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


def _is_test(path: str) -> bool:
    return bool(re.search(r"(^|/)(tests?|__tests__|spec)/|(_test|\.test|\.spec|_spec)\.|(^|/)test_[^/]+$", path, re.I))


def _is_migration(path: str) -> bool:
    return bool(re.search(r"(^|/)migrations?/|(^|/)alembic/|\.migration", path, re.I))


def _is_changelog(path: str) -> bool:
    return bool(re.search(r"changelog", path, re.I))


def _is_version(path: str) -> bool:
    base = path.rsplit("/", 1)[-1].lower()
    return base in ("package.json", "pyproject.toml", "setup.py", "setup.cfg",
                    "version", "version.txt", "version.py", "__version__.py", "cargo.toml")


def _is_docs(path: str) -> bool:
    return bool(re.search(r"(^|/)docs?/|readme", path, re.I) or path.lower().endswith(".md"))


def _is_source(path: str) -> bool:
    return path.lower().endswith(CODE_EXT) and not _is_test(path) and not _is_migration(path)


def parse_diff(title: str, description: str, diff: str) -> dict:
    diff = diff or ""
    changed_files: List[str] = []
    added, removed = 0, 0
    added_lines: List[str] = []
    cur = None
    per_file_added: dict = {}

    for raw in diff.splitlines():
        m = re.match(r"^diff --git a/(.+?) b/(.+)$", raw)
        if m:
            cur = m.group(2).strip()
            if cur not in changed_files:
                changed_files.append(cur)
                per_file_added[cur] = []
            continue
        m = re.match(r"^\+\+\+ b/(.+)$", raw)
        if m:
            cur = m.group(1).strip()
            if cur != "/dev/null" and cur not in changed_files:
                changed_files.append(cur)
                per_file_added.setdefault(cur, [])
            continue
        if raw.startswith("--- "):
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            added += 1
            line = raw[1:]
            added_lines.append(line)
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

    # new endpoints (evidence: "file: line")
    new_endpoints: List[str] = []
    for f in changed_files:
        for ln in per_file_added.get(f, []):
            if any(re.search(p, ln) for p in ENDPOINT_PATTERNS):
                new_endpoints.append(f"{f}: {ln.strip()[:120]}")

    # migration down/rollback path present?
    migration_has_down = False
    for f in migration_files:
        blob = "\n".join(per_file_added.get(f, []))
        if re.search(r"\b(downgrade|rollback)\b|def\s+down\b|\bdown\s*\(|--\s*down|down\s*=", blob, re.I):
            migration_has_down = True
            break

    # secrets in added lines (redacted evidence)
    secrets_found: List[str] = []
    for ln in added_lines:
        for pat, label in SECRET_PATTERNS:
            if re.search(pat, ln):
                secrets_found.append(f"{label}: {ln.strip()[:60]}")
                break

    # debug leftovers in added lines
    debug_leftovers: List[str] = []
    for ln in added_lines:
        for pat, label in DEBUG_PATTERNS:
            if re.search(pat, ln):
                debug_leftovers.append(f"{label}: {ln.strip()[:80]}")
                break

    has_source_change = len(source_files) > 0 or len(new_endpoints) > 0
    has_new_source_code = any(
        re.search(r"\bdef\s+\w+\s*\(|\bfunction\s+\w+\s*\(|\bfunc\s+\w+\s*\(|=>\s*\{|\bclass\s+\w+", ln)
        for f in source_files for ln in per_file_added.get(f, [])
    ) or len(new_endpoints) > 0

    return {
        "changed_files": changed_files,
        "added_lines": added,
        "removed_lines": removed,
        "migration_files": migration_files,
        "test_files": test_files,
        "changelog_files": changelog_files,
        "version_files": version_files,
        "docs_files": docs_files,
        "source_files": source_files,
        "new_endpoints": new_endpoints[:10],
        "migration_has_down": migration_has_down,
        "secrets_found": secrets_found[:10],
        "debug_leftovers": debug_leftovers[:10],
        "has_source_change": has_source_change,
        "has_new_source_code": has_new_source_code,
    }


class ParsePrInput(BaseModel):
    title: str = ""
    description: str = ""
    diff: str = ""


class ParsePrResult(BaseModel):
    changed_files: List[str]
    added_lines: int
    removed_lines: int
    migration_files: List[str]
    test_files: List[str]
    changelog_files: List[str]
    version_files: List[str]
    docs_files: List[str]
    source_files: List[str]
    new_endpoints: List[str]
    migration_has_down: bool
    secrets_found: List[str]
    debug_leftovers: List[str]
    has_source_change: bool
    has_new_source_code: bool


async def parse_pr(ctx: FunctionContext, data: ParsePrInput) -> ParsePrResult:
    """Normalise a unified diff and extract the signals the checklist scores on.
    Pure and deterministic — no pod access, no LLM. Testable on any pasted diff."""
    parsed = parse_diff(data.title, data.description, data.diff)
    return ParsePrResult(**parsed)
