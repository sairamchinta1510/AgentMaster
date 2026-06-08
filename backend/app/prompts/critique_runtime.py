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
non-placeholder values, the verdict MUST be APPROVED unless:
  a) There is a critical security vulnerability (hardcoded secrets, SQL injection, etc.)
  b) The output values are factually wrong or contradicted by the task description
  c) A required output field is missing entirely or contains only 'unknown'/'placeholder'/'N/A'/'none'
Do NOT flag NEEDS_FIX based on coding style, pattern preferences, or "should compute vs read from env var"
when the actual output is correct. Judge the OUTPUT, not the implementation approach.

Evaluate:
1. (MOST IMPORTANT) Are all output fields present in stdout with valid, meaningful values?
2. Does the output fulfil the agent's stated purpose: {agent_description}?
3. Are there ACTUAL correctness errors (wrong values, missing data, failed task goal)?
4. Are there critical security issues (hardcoded secrets, command injection)?
5. Is the output useful and actionable for the next agent in the pipeline?

If verdict is NEEDS_FIX, fix_instructions must describe a CONCRETE CORRECTNESS problem.
Do NOT instruct the agent to change code style, refactor patterns, or remove env var reads if output is correct."""
