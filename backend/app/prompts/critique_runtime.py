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

CRITICAL ENV VAR RULES (violations = automatic NEEDS_FIX):
1. CORRECT — reading any of the valid env vars listed above via os.environ is ALWAYS valid.
   e.g. os.environ["REPOSITORY_PATH"], os.environ["REPOSITORY_URL"] are both correct.
   Do NOT flag these as errors — they are the intended access pattern.
2. WRONG — reading OUTPUT schema fields ({output_keys}) from os.environ.
   Output fields must be COMPUTED/PRODUCED by the code, never read from os.environ.
   e.g. if "log_storage_mechanism" is an output field, os.environ["LOG_STORAGE_MECHANISM"] is WRONG.

Evaluate:
1. Does the code produce all OUTPUT schema fields by computing them (not reading from os.environ)?
2. Does the output fulfil the agent's stated purpose: {agent_description}?
3. Is the approach industry-standard for this domain?
4. Are there security, reliability, or correctness issues?
5. Is the output complete and actionable (not 'unknown', empty, or placeholder)?

If verdict is NEEDS_FIX, fix_instructions must tell the agent exactly how to fix its code.
IMPORTANT: Do NOT instruct the agent to remove os.environ reads for valid env vars — only flag output field reads."""
