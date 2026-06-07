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
        return CritiqueResult(
            critique_id=data.get(
                "critique_id", f"{agent.agent_id}_critique_iter_{iteration}"
            ),
            target_agent=agent.agent_id,
            target_agent_name=agent.agent_name,
            phase=phase,
            iteration=iteration,
            max_iterations=5,
            verdict=CritiqueVerdict(data["verdict"]),
            quality_score=float(data.get("quality_score", 0)),
            errors_remaining=int(data.get("errors_remaining", 0)),
            issues=issues,
            approved_aspects=data.get("approved_aspects", []),
            improvements_made=data.get("improvements_made_this_iteration", []),
            remaining_errors=data.get("remaining_errors", []),
            suggested_new_agents=data.get("suggested_new_agents", []),
            missing_user_inputs=data.get("missing_user_inputs", []),
        )


async def run_critique_loop(
    agent: AtomicAgent,
    critique_agent: AgentCritiqueAgent,
    producer_agent,
    phase: str,
    max_iterations: int = 5,
    on_event=None,
) -> tuple[CritiqueResult, AtomicAgent, int]:
    """Run the up-to-5-iteration critique loop.

    Returns (final_result, final_agent, iterations_used).
    Errors NEVER pass forward — escalates after max_iterations if still failing.
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
            return result, agent, iteration

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

    return final_result, agent, max_iterations
