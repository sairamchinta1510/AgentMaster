"""LLM prompts for the runtime Critique Agent node.

Two variants:
- build_design_critique_prompt: validates agent spec/schema at design time
- build_run_critique_prompt:    validates execution output at run time
"""
import json


_CRITIQUE_SYSTEM = """You are a world-class expert reviewing an AI agent.
Your job: evaluate the agent against industry best standards for its specific domain.
Be precise and actionable. Never fix the code yourself — only give instructions.

Return ONLY valid JSON:
{
  "verdict": "APPROVED" or "NEEDS_FIX",
  "quality_score": <1-10>,
  "issues": ["specific issue 1", ...],
  "fix_instructions": "Precise instructions for the agent to fix its approach. Empty string if APPROVED."
}"""


def build_design_critique_prompt(
    agent_name: str,
    agent_description: str,
    input_schema: dict,
    output_schema: dict,
) -> str:
    return f"""{_CRITIQUE_SYSTEM}

MODE: Design-time — validate the agent's specification and schema.

Agent: {agent_name}
Description: {agent_description}
Input Schema: {json.dumps(input_schema, indent=2)}
Output Schema: {json.dumps(output_schema, indent=2)}

Evaluate:
1. Does the description clearly describe ONE atomic task aligned with industry standards for this domain?
2. Is the input schema complete — are all required inputs present?
3. Is the output schema meaningful — does it capture what this agent should produce?
4. Are there schema fields that belong in the OTHER schema (e.g. output fields used as inputs)?
5. Is the agent's approach industry-standard for: {agent_description}?

If verdict is NEEDS_FIX, fix_instructions must tell the agent exactly what to change in its spec/schema."""


def build_run_critique_prompt(
    agent_name: str,
    agent_description: str,
    input_schema: dict,
    output_schema: dict,
    actual_inputs: dict,
    code: str,
    stdout: str,
    stderr: str,
    returncode: int,
) -> str:
    output_keys = [k.upper() for k in output_schema.keys()]
    # Every context key (input schema fields + upstream outputs) is a valid env var
    valid_env_var_lines = "\n  ".join(
        f"{k.upper()} = {str(v)[:80]}"
        for k, v in actual_inputs.items()
        if not k.startswith("_")
    )

    return f"""{_CRITIQUE_SYSTEM}

MODE: Run-time — validate the agent's execution output.

Agent: {agent_name}
Description: {agent_description}
Input Schema: {json.dumps(input_schema, indent=2)}
Output Schema: {json.dumps(output_schema, indent=2)}

Valid env vars (ALL of these are correctly readable via os.environ["KEY"]):
  {valid_env_var_lines or "(none)"}

Code executed:
```python
{code[:1000] + ("\n... (truncated)" if len(code) > 1000 else "")}
```
Stdout: {stdout[:500] or "(empty)"}
Stderr: {stderr[:500] or "(none)"}
Return code: {returncode}

ENV VAR RULES:
1. CORRECT — reading any of the valid env vars listed above via os.environ is ALWAYS valid.
   e.g. os.environ["REPOSITORY_PATH"], os.environ["REPOSITORY_URL"] are both correct.
   Do NOT flag these as errors — they are the intended access pattern.
2. Reading output schema fields from os.environ as a FALLBACK (e.g. `value = os.environ.get("FOO") or compute()`)
   is acceptable if the agent produces correct output.

OUTCOME-FIRST EVALUATION RULE (HIGHEST PRIORITY):
If return_code = 0 AND all output schema fields ({output_keys}) are present in stdout with non-empty,
non-placeholder values, the verdict MUST be APPROVED unless any of the AUTOMATIC FAIL conditions below apply.

AUTOMATIC FAIL — flag NEEDS_FIX immediately if ANY of these are true:
  a) fix_description says "Could not find" or "snippet not found" or "no changes made" — agent failed its goal
  b) fixed_snippet contains placeholder text: "YOUR_NEW_", "PLACEHOLDER", "TODO", "FIXME",
     or nonsensical repeated patterns — the fix is invalid
  c) The fix renames environment variable names (e.g. GEMINI_API_KEY → anything else) — NEVER acceptable
  d) A required output field is missing or contains only 'unknown'/'none'/'N/A'
  e) Critical security vulnerability introduced (hardcoded secrets, command injection)
  f) DESTRUCTIVE CHANGE: fixed_snippet is more than 30% shorter than original_snippet in character count,
     OR fixed_snippet is missing lines that were in original_snippet and those lines were not the bug.
     A code fix must ADD lines, never delete working code. If the fix removed a try/catch block,
     removed function body, or deleted more than 3 lines of working logic — this is AUTOMATIC FAIL.
     Fix instructions: "Only INSERT new lines after the anchor line using content.replace(anchor, anchor+insertion, 1).
     Do NOT delete existing try/catch blocks, function bodies, or any working code.
     The fixed file MUST be longer than the original."

Do NOT flag NEEDS_FIX based on coding style or pattern preferences when the actual output is correct.

Evaluate:
1. (MOST IMPORTANT) Are all output fields present with valid, meaningful, non-placeholder values?
2. Does the fix ADD new error handling without deleting existing working code?
3. Is fixed_snippet longer than or equal in length to original_snippet? (fixes add lines, not remove)
4. Is the output useful and actionable for the next agent in the pipeline?

If verdict is NEEDS_FIX, fix_instructions must be specific: tell the agent EXACTLY:
  - Which anchor line to use (verbatim)
  - What lines to INSERT after the anchor
  - That they must use content.replace(anchor, anchor + insertion, 1) — NOT replace a multi-line block
  - That the fixed file must be LONGER than the original (assertion: len(new) > len(old))"""
