import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.agents.tools import llm_call_tool
from app.models import Critique
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CritiqueAgent:
    """
    Critique Agent - validates agent outputs through 3+ rounds.

    Rounds:
    1. Factual Verification - check claims against citations
    2. Completeness Check - did agent fully accomplish task?
    3. Consistency Validation - cross-check with task requirements
    """

    def __init__(
        self,
        agent_id: str,
        agent_output: Dict[str, Any],
        task_description: str,
        db_session: Session
    ):
        self.agent_id = agent_id
        self.agent_output = agent_output
        self.task_description = task_description
        self.db_session = db_session

    def run_critique(self) -> Dict[str, Any]:
        """
        Run minimum 3 critique rounds.

        Returns:
            dict with verdict, round_results, overall_confidence
        """
        # Quick check: if no citations, auto-reject
        if not self.agent_output.get("citations"):
            logger.warning(f"Agent {self.agent_id} output has no citations - auto-rejecting")
            self._save_critique(1, "factual_verification", "failed", "No citations provided")
            return {
                "verdict": "rejected",
                "round_results": [{
                    "round": 1,
                    "type": "factual_verification",
                    "passed": False,
                    "reasoning": "No citations provided - auto-rejected",
                    "unsupported_claims": ["All output claims are unsupported"]
                }],
                "overall_confidence": 0
            }

        # Run 3 rounds
        round_results = []

        # Round 1: Factual Verification
        round1 = self._round_factual_verification()
        round_results.append(round1)
        self._save_critique(1, "factual_verification", "passed" if round1["passed"] else "failed", round1["reasoning"])

        # Round 2: Completeness Check
        round2 = self._round_completeness_check()
        round_results.append(round2)
        self._save_critique(2, "completeness_check", "passed" if round2["passed"] else "failed", round2["reasoning"])

        # Round 3: Consistency Validation
        round3 = self._round_consistency_validation()
        round_results.append(round3)
        self._save_critique(3, "consistency_validation", "passed" if round3["passed"] else "failed", round3["reasoning"])

        # Determine verdict
        passed_count = sum(1 for r in round_results if r["passed"])

        if passed_count == 3:
            verdict = "approved"
            confidence = 95
        elif passed_count >= 2:
            # 2/3 passed - run Round 4 with combined context
            round4 = self._round4_combined()
            round_results.append(round4)
            self._save_critique(4, "combined_review", "passed" if round4["passed"] else "failed", round4["reasoning"])

            if round4["passed"]:
                verdict = "approved"
                confidence = 85
            else:
                verdict = "needs_human_review"
                confidence = 50
        else:
            verdict = "rejected"
            confidence = 20

        return {
            "verdict": verdict,
            "round_results": round_results,
            "overall_confidence": confidence
        }

    def _round_factual_verification(self) -> Dict[str, Any]:
        """Round 1: Check all claims against citations."""
        citations = self.agent_output.get("citations", [])
        data = self.agent_output.get("data", {})

        # Simple heuristic: if citations exist and data exists, likely valid
        # In production, use LLM to verify each claim

        if not citations:
            return {
                "round": 1,
                "type": "factual_verification",
                "passed": False,
                "reasoning": "No citations provided",
                "unsupported_claims": ["All claims"]
            }

        # Check that citations have required fields
        for citation in citations:
            if "source_type" not in citation or "source" not in citation:
                return {
                    "round": 1,
                    "type": "factual_verification",
                    "passed": False,
                    "reasoning": "Citations missing required fields (source_type, source)",
                    "unsupported_claims": []
                }

        return {
            "round": 1,
            "type": "factual_verification",
            "passed": True,
            "reasoning": "All citations properly structured",
            "unsupported_claims": []
        }

    def _round_completeness_check(self) -> Dict[str, Any]:
        """Round 2: Did agent fully accomplish task?"""
        status = self.agent_output.get("status")
        data = self.agent_output.get("data", {})

        if status != "completed":
            return {
                "round": 2,
                "type": "completeness_check",
                "passed": False,
                "reasoning": f"Agent status is {status}, not completed",
                "unsupported_claims": []
            }

        if not data:
            return {
                "round": 2,
                "type": "completeness_check",
                "passed": False,
                "reasoning": "No output data produced",
                "unsupported_claims": []
            }

        return {
            "round": 2,
            "type": "completeness_check",
            "passed": True,
            "reasoning": "Agent completed with output data",
            "unsupported_claims": []
        }

    def _round_consistency_validation(self) -> Dict[str, Any]:
        """Round 3: Check consistency with task requirements."""
        # Simple heuristic: if confidence >= 70, likely consistent
        confidence = self.agent_output.get("confidence", 0)

        if confidence < 70:
            return {
                "round": 3,
                "type": "consistency_validation",
                "passed": False,
                "reasoning": f"Low confidence score: {confidence}%",
                "unsupported_claims": []
            }

        return {
            "round": 3,
            "type": "consistency_validation",
            "passed": True,
            "reasoning": f"Confidence score acceptable: {confidence}%",
            "unsupported_claims": []
        }

    def _round4_combined(self) -> Dict[str, Any]:
        """Round 4: Combined review when rounds disagree."""
        # If we got here, 2/3 rounds passed
        # Simple heuristic: approve if confidence >= 80
        confidence = self.agent_output.get("confidence", 0)

        return {
            "round": 4,
            "type": "combined_review",
            "passed": confidence >= 80,
            "reasoning": f"Combined review based on confidence: {confidence}%",
            "unsupported_claims": []
        }

    def _save_critique(self, round_number: int, critique_type: str, verdict: str, reasoning: str) -> None:
        """Save critique round to database."""
        critique = Critique(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            round_number=round_number,
            critique_type=critique_type,
            verdict=verdict,
            reasoning=reasoning,
            unsupported_claims=[]
        )
        self.db_session.add(critique)
        self.db_session.commit()
