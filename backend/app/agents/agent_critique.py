import json
import logging
from openai import AsyncOpenAI
from app.config import settings
from app.prompts.critique import get_critique_prompt
from app.models.agent import AtomicAgent, CritiqueResult, CritiqueVerdict, CritiqueIssue
from app.agents.llm_utils import stream_llm_json

logger = logging.getLogger(__name__)


def make_llm_client() -> tuple[AsyncOpenAI, str]:
    return AsyncOpenAI(
        api_key=settings.active_api_key,
        base_url=settings.active_base_url,
    ), settings.active_model


class AgentCritiqueAgent:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or ""
        if api_key == "fake":
            self.client = None
            self.model = "fake"
        else:
            self.client, self.model = make_llm_client()

    async def _call_llm(
        self,
        agent: AtomicAgent,
        phase: str,
        iteration: int,
        previous_issues: list | None = None,
        on_event=None,
    ) -> dict:
        prompt = get_critique_prompt(
            agent.model_dump(exclude={"critique_history"}), phase, iteration, previous_issues
        )
        assert self.client is not None
        content = await stream_llm_json(
            self.client, self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Critique agent {agent.agent_name} — iteration {iteration} of 5"},
            ],
            temperature=0.1,
            on_event=on_event,
            context=f"Critiquing {agent.agent_name} (round {iteration})",
        )
        return json.loads(content)

    async def critique(
        self,
        agent: AtomicAgent,
        phase: str,
        iteration: int,
        previous_issues: list | None = None,
        on_event=None,
    ) -> CritiqueResult:
        data = await self._call_llm(agent, phase, iteration, previous_issues, on_event=on_event)
        issues = [CritiqueIssue(**i) for i in data.get("issues", [])]
        # Normalise verdict: LLM sometimes returns "NEEDS_FIX" instead of "NEEDS_REVISION"
        _VERDICT_MAP = {"NEEDS_FIX": "NEEDS_REVISION", "FIX": "NEEDS_REVISION",
                        "REJECT": "NEEDS_REVISION", "FAIL": "NEEDS_REVISION"}
        raw_verdict = data.get("verdict", "NEEDS_REVISION")
        raw_verdict = _VERDICT_MAP.get(raw_verdict, raw_verdict)
        try:
            verdict_val = CritiqueVerdict(raw_verdict)
        except ValueError:
            verdict_val = CritiqueVerdict.NEEDS_REVISION
        return CritiqueResult(
            critique_id=data.get(
                "critique_id", f"{agent.agent_id}_critique_iter_{iteration}"
            ),
            target_agent=agent.agent_id,
            target_agent_name=agent.agent_name,
            phase=phase,
            iteration=iteration,
            max_iterations=5,
            verdict=verdict_val,
            quality_score=float(data.get("quality_score", 0)),
            errors_remaining=int(data.get("errors_remaining", 0)),
            issues=issues,
            approved_aspects=data.get("approved_aspects", []),
            improvements_made=data.get("improvements_made_this_iteration", []),
            remaining_errors=data.get("remaining_errors", []),
            suggested_new_agents=data.get("suggested_new_agents", []),
            missing_user_inputs=data.get("missing_user_inputs", []),
        )


async def decompose_agent(
    original: AtomicAgent,
    suggested: list[dict],
    producer_agent,
    critique_agent: AgentCritiqueAgent,
    phase: str,
    on_event=None,
) -> list[AtomicAgent]:
    """Produce and critique each suggested sub-agent, returning all approved ones.

    Sub-agent critique loops run with allow_decompose=False to prevent
    infinite recursion — sub-agents cannot themselves be decomposed further.
    """
    results: list[AtomicAgent] = []
    for idx, spec in enumerate(suggested, 1):
        sub_id = f"{original.agent_id}_part_{idx}"
        full_spec = {
            "agent_id": sub_id,
            "agent_name": spec.get("agent_name", f"SubAgent{idx}"),
            "description": spec.get("description", ""),
            "input_schema": spec.get("input_schema", {}),
            "output_schema": spec.get("output_schema", {}),
            "depends_on": [],
            "timeout_seconds": 60,
        }
        if on_event:
            await on_event("PHASE_UPDATE", {
                "phase": "DECOMPOSING",
                "message": f"Decomposing into sub-agent {idx}/{len(suggested)}: {full_spec['agent_name']}…",
            })
        sub_agent = await producer_agent.produce(
            full_spec, phase, original.session_id, on_event=on_event
        )
        _result, approved, _iters = await run_critique_loop(
            sub_agent, critique_agent, producer_agent, phase,
            on_event=on_event, allow_decompose=False,
        )
        results.extend(approved)
    return results


async def run_critique_loop(
    agent: AtomicAgent,
    critique_agent: AgentCritiqueAgent,
    producer_agent,
    phase: str,
    max_iterations: int = 5,
    on_event=None,
    allow_decompose: bool = True,
) -> tuple[CritiqueResult, list[AtomicAgent], int]:
    """Run the up-to-5-iteration critique loop.

    Returns (final_result, list[AtomicAgent], iterations_used).
    Normally returns a list of 1 agent. If an atomicity violation persists
    on iteration 2+ and suggested_new_agents is populated, decomposes the
    agent and returns N sub-agents instead. allow_decompose=False prevents
    infinite recursion in nested calls.
    """
    previous_issues: list[dict] = []
    final_result: CritiqueResult | None = None

    for iteration in range(1, max_iterations + 1):
        if on_event:
            await on_event("PHASE_UPDATE", {
                "phase": f"DESIGN_CRITIQUE_{iteration}",
                "message": f"Critique round {iteration}/5 — calling LLM to review {agent.agent_name}…",
            })
        result = await critique_agent.critique(
            agent, phase, iteration, previous_issues or None, on_event=on_event
        )
        agent.critique_iterations = iteration
        agent.critique_history.append(result)
        final_result = result

        if result.verdict == CritiqueVerdict.APPROVED:
            agent.quality_score = result.quality_score
            if on_event:
                await on_event("PHASE_UPDATE", {
                    "phase": "APPROVED",
                    "message": f"{agent.agent_name} approved ★{result.quality_score}/10 after {iteration} round(s)",
                })
            return result, [agent], iteration

        has_atomicity_issue = any(i.category == "atomicity" for i in result.issues)
        if (
            allow_decompose
            and iteration >= 2
            and has_atomicity_issue
            and result.suggested_new_agents
        ):
            if on_event:
                await on_event("PHASE_UPDATE", {
                    "phase": "DECOMPOSING",
                    "message": (
                        f"{agent.agent_name} has persistent atomicity violation — "
                        f"decomposing into {len(result.suggested_new_agents)} sub-agent(s)…"
                    ),
                })
            sub_agents = await decompose_agent(
                agent, result.suggested_new_agents, producer_agent,
                critique_agent, phase, on_event=on_event,
            )
            if sub_agents:
                return result, sub_agents, iteration

        previous_issues = [i.model_dump() for i in result.issues]
        if iteration < max_iterations:
            if on_event:
                await on_event("PHASE_UPDATE", {
                    "phase": "REVISING_SPEC",
                    "message": f"Auto-fixing {len(result.issues)} issue(s) in {agent.agent_name} — calling LLM…",
                })
            agent = await producer_agent.revise(agent, previous_issues, phase, on_event=on_event)

    # After max_iterations — escalate: errors must NEVER pass forward
    assert final_result is not None
    if final_result.errors_remaining > 0:
        final_result.verdict = CritiqueVerdict.ESCALATE_AUTO_FIX

    return final_result, [agent], max_iterations
