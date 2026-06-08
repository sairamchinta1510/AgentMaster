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
    input_keys_upper = [k.upper() for k in input_schema.keys()]

    return f"""{_CRITIQUE_SYSTEM}

MODE: Run-time — validate the agent's execution output.

Agent: {agent_name}
Description: {agent_description}
Input Schema: {json.dumps(input_schema, indent=2)}
Output Schema: {json.dumps(output_schema, indent=2)}

Actual inputs available (as env vars): {json.dumps(actual_inputs, indent=2)}
Code executed:
```python
{code[:1000] + ("\n... (truncated)" if len(code) > 1000 else "")}
```
Stdout: {stdout[:500] or "(empty)"}
Stderr: {stderr[:500] or "(none)"}
Return code: {returncode}

CRITICAL CHECKS:
- Output schema fields ({output_keys}) must be PRODUCED by the agent, not read from os.environ
- Only input schema fields ({input_keys_upper}) should be read from os.environ
- Reading an output field as os.environ['FIELD'] is ALWAYS wrong

Evaluate:
1. Does the code correctly read only INPUT schema fields from os.environ? (not output fields)
2. Does the output fulfil the agent's stated purpose: {agent_description}?
3. Is the approach industry-standard for this domain?
4. Are there security, reliability, or correctness issues?
5. Is the output complete and actionable (not 'unknown' or empty)?

If verdict is NEEDS_FIX, fix_instructions must tell the agent exactly how to fix its code."""
