"""Chain-of-Thought reasoning pipeline for higher quality LLM analysis.

Instead of: one prompt → one output
Does: extract facts → validate → generate insight

This reduces hallucination by forcing the LLM to show its work.
"""
import json
import logging
from backend.llm.ollama_client import ollama_client
from backend.analysis.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ChainOfThought:
    """Multi-step reasoning pipeline for code analysis."""

    async def analyze(
        self,
        code_context: str,
        analysis_prompt: str,
        task: str = "deep",
        model: str = None,
    ) -> dict:
        """Run 3-step chain-of-thought analysis.

        Step 1: Extract raw facts from the code
        Step 2: Validate facts against the actual code
        Step 3: Generate structured insight from validated facts
        """
        # Step 1: Fact extraction
        facts = await self._extract_facts(code_context, task, model)
        logger.info(f"CoT Step 1 ({task}): extracted {len(facts)} facts")

        # Step 2: Validation
        validated = await self._validate_facts(facts, code_context, model)
        logger.info(f"CoT Step 2 ({task}): {len(validated)} validated facts")

        # Step 3: Generate final insight using validated facts + original prompt
        result = await self._generate_insight(validated, analysis_prompt, code_context, model)
        result["_cot_meta"] = {
            "facts_extracted": len(facts),
            "facts_validated": len(validated),
            "reasoning_steps": 3,
        }
        return result

    async def _extract_facts(self, code_context: str, task: str, model: str = None) -> list[str]:
        """Step 1: Extract concrete facts from the code."""
        prompt = f"""You are analyzing source code. Extract ONLY concrete, verifiable facts.

Code Context:
{code_context}

Rules:
- Each fact must be directly observable in the code
- No assumptions or inferences
- Include file paths, function names, patterns you see
- Be specific: "uses Express.js router" not "uses a framework"

Respond in JSON:
{{"facts": ["fact 1", "fact 2", ...]}}"""

        try:
            result = await ollama_client.generate_json(prompt, system_prompt=SYSTEM_PROMPT, model=model)
            if isinstance(result, dict) and "facts" in result:
                return result["facts"]
            if isinstance(result, list):
                return result
            return [str(result.get("raw_response", ""))] if "raw_response" in result else []
        except Exception as e:
            logger.warning(f"Fact extraction failed: {e}")
            return []

    async def _validate_facts(self, facts: list[str], code_context: str, model: str = None) -> list[str]:
        """Step 2: Cross-check facts against the actual code."""
        if not facts:
            return []

        facts_str = "\n".join(f"- {f}" for f in facts)
        prompt = f"""You are a code reviewer. Check each fact against the actual code.

Extracted facts:
{facts_str}

Actual code context:
{code_context[:3000]}

For each fact, determine if it is:
- CONFIRMED: directly visible in the code
- UNVERIFIED: plausible but not directly confirmed
- FALSE: contradicted by the code

Return ONLY confirmed and unverified facts. Remove false ones.

Respond in JSON:
{{"validated_facts": ["fact 1", "fact 2", ...], "removed": ["false fact 1", ...]}}"""

        try:
            result = await ollama_client.generate_json(prompt, system_prompt=SYSTEM_PROMPT, model=model)
            if isinstance(result, dict) and "validated_facts" in result:
                return result["validated_facts"]
            return facts  # Fallback: return original facts if validation fails
        except Exception as e:
            logger.warning(f"Fact validation failed: {e}")
            return facts  # Fallback: return original facts

    async def _generate_insight(
        self,
        validated_facts: list[str],
        analysis_prompt: str,
        code_context: str,
        model: str = None,
    ) -> dict:
        """Step 3: Generate structured insight from validated facts."""
        facts_str = "\n".join(f"- {f}" for f in validated_facts) if validated_facts else "No facts extracted"

        enhanced_prompt = f"""You have verified the following facts about this code:

Validated Facts:
{facts_str}

Now, using ONLY these validated facts and the code below, complete the analysis.
Do NOT add information beyond what the facts support. If unsure, lower your confidence score.

{analysis_prompt}"""

        try:
            result = await ollama_client.generate_json(enhanced_prompt, system_prompt=SYSTEM_PROMPT, model=model)
            return result
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return {"error": str(e), "raw_facts": validated_facts}

    async def quick_analyze(
        self,
        code_context: str,
        analysis_prompt: str,
        model: str = None,
    ) -> dict:
        """Single-step analysis for fast tasks (no CoT overhead)."""
        try:
            return await ollama_client.generate_json(analysis_prompt, system_prompt=SYSTEM_PROMPT, model=model)
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}")
            return {"error": str(e)}


cot_pipeline = ChainOfThought()
