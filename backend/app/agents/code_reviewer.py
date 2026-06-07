"""Runtime code reviewer for LLM-generated agent code.

Sits between PLAN and EXEC in AgentExecutorAgent:
  PLAN → REVIEW → EXEC → SYNTH

fix_missing_imports()  — zero-LLM: auto-injects missing stdlib imports
detect_code_issues()   — zero-LLM: static analysis for unsafe patterns
review_and_fix_code()  — LLM fix only when issues found
"""
import json
import logging
import re

logger = logging.getLogger(__name__)

# Standard library modules whose usage we can detect and auto-import
_STDLIB_MODULES = [
    "sys", "os", "json", "re", "subprocess", "pathlib",
    "tempfile", "glob", "shutil", "datetime", "time", "uuid",
]

# Regex for hardcoded /tmp/<name> paths (not using tempfile)
_HARDCODED_TMP_RE = re.compile(r'["\']\/tmp\/\w+')

# Regex for destructive shell/fs operations
_DESTRUCTIVE_RE = re.compile(
    r'(?:'
    r'subprocess\.[^\n]*["\']rm["\'][^\n]*-rf'          # rm -rf via subprocess
    r'|["\'`]rm\s+-rf'                                   # rm -rf as string
    r'|shutil\.rmtree\s*\(\s*(?!.*tempfile|.*mkdtemp)'  # rmtree on non-tempdir
    r')',
    re.DOTALL,
)

_REVIEW_SYSTEM_PROMPT = """You are a code safety reviewer. Fix the issues listed below in the Python code.

Rules:
- Replace hardcoded /tmp/<name> paths with tempfile.mkdtemp()
- Replace hardcoded input values with os.environ["INPUT_NAME"] reads
- Remove or neutralise destructive commands (rm -rf, shutil.rmtree on system paths)
- Keep all other logic identical

Return ONLY valid JSON:
{"fixed_code": "<corrected python>", "changes": ["change description", ...]}
"""


def fix_missing_imports(code: str) -> tuple[str, list[str]]:
    """Auto-inject missing stdlib imports at the top of the code.

    Scans for module usage (e.g. ``sys.``, ``json.``) and prepends
    ``import <module>`` for any that are used but not already imported.
    No LLM call required.
    """
    changes: list[str] = []
    to_add: list[str] = []
    for module in _STDLIB_MODULES:
        used = bool(re.search(rf'\b{re.escape(module)}\.', code))
        # Match both `import module` and `import a, module, b` forms
        already_imported = bool(
            re.search(rf'\bimport\s[^\n]*\b{re.escape(module)}\b', code)
            or re.search(rf'from\s+{re.escape(module)}\s+import', code)
        )
        if used and not already_imported:
            to_add.append(f"import {module}")
            changes.append(f"Added missing import: {module}")
    if to_add:
        code = "\n".join(to_add) + "\n" + code
    return code, changes


def detect_code_issues(code: str, available_inputs: dict) -> list[str]:
    """Return a list of issue descriptions found via static analysis. Empty = clean."""
    issues: list[str] = []

    # 1. Hardcoded /tmp/<name> without tempfile.mkdtemp()
    if _HARDCODED_TMP_RE.search(code) and "tempfile.mkdtemp" not in code:
        issues.append(
            "Hardcoded /tmp path detected — use tempfile.mkdtemp() to avoid collisions across runs"
        )

    # 2. Destructive operations — rmtree/rm -rf on non-temp paths
    _RMTREE_RE = re.compile(r'shutil\.rmtree|["\'`]rm\s+-rf|subprocess\.[^\n]*["\']rm["\'][^\n]*-rf')
    if _RMTREE_RE.search(code) and "tempfile" not in code:
        issues.append(
            "Potentially destructive file operation (rm -rf / shutil.rmtree) on a non-temp path"
        )

    # 3. Hardcoded values that match available inputs
    for key, value in available_inputs.items():
        if not isinstance(value, str) or len(value) < 8:
            continue
        if value in code and f'os.environ' not in code:
            issues.append(
                f"Input '{key.lower()}' appears hardcoded — "
                f"read it from os.environ['{key.upper()}'] instead"
            )

    return issues


async def review_and_fix_code(
    code: str,
    available_inputs: dict,
    client,
    model: str,
) -> tuple[str, list[str]]:
    """Review code for issues and fix via LLM if needed.

    Steps (in order, zero-LLM first):
    1. fix_missing_imports — auto-inject missing stdlib imports
    2. detect_code_issues  — static analysis for unsafe patterns
    3. If issues found → LLM fix pass; otherwise return immediately

    Returns (final_code, list_of_changes).
    Falls back to original code if LLM fix fails — never crashes.
    """
    all_changes: list[str] = []

    # Step 1: auto-fix missing imports (no LLM)
    code, import_changes = fix_missing_imports(code)
    all_changes.extend(import_changes)

    # Step 2: static analysis
    issues = detect_code_issues(code, available_inputs)
    if not issues:
        return code, all_changes

    logger.info("Code review found %d issue(s); requesting LLM fix", len(issues))

    prompt = (
        f"Issues found:\n"
        + "\n".join(f"- {i}" for i in issues)
        + f"\n\nAvailable inputs (readable via os.environ): {list(available_inputs.keys())}"
        + f"\n\nCode to fix:\n```python\n{code}\n```"
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        fixed = data.get("fixed_code", "").strip()
        changes: list[str] = data.get("changes", [])
        if not fixed:
            raise ValueError("LLM returned empty fixed_code")
        logger.info("Code reviewer applied %d change(s): %s", len(changes), changes)
        all_changes.extend(changes)
        return fixed, all_changes
    except Exception as exc:
        logger.warning("Code reviewer failed (%s); using pre-LLM code", exc)
        return code, all_changes
