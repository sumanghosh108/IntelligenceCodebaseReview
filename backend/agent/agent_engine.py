"""Autonomous Agent Engine — ReAct-style reasoning loop for codebase exploration.

Inspired by LangGraph's state-machine approach but built lightweight for Ollama.

Flow:
  1. User asks a question
  2. Agent plans exploration steps (THINK)
  3. Agent selects and calls tools (ACT)
  4. Agent observes results (OBSERVE)
  5. Agent decides: explore more or synthesize answer (DECIDE)
  6. Repeat 2-5 until confident, then return final answer

Each step is yielded as a structured event so the frontend can show real-time progress.
"""
import json
import re
import logging
import time
from typing import AsyncGenerator

from backend.agent.tools import AgentTools
from backend.llm.model_router import model_router

logger = logging.getLogger(__name__)

# Maximum reasoning steps before forcing a final answer
MAX_STEPS = 5
# Maximum total prompt size (chars) before compressing history
MAX_PROMPT_CHARS = 6000

AGENT_SYSTEM_PROMPT = """You are an expert code analysis agent. You explore codebases autonomously to answer user questions.

You have access to these tools:
{tools}

## How to respond

At each step, you MUST respond with EXACTLY ONE of these formats:

### To use a tool:
THINK: <your reasoning about what to explore next>
ACTION: <tool_name>
INPUT: <tool input>

### To give the final answer (when you have enough information):
THINK: <your reasoning about why you have enough info>
ANSWER: <your comprehensive answer to the user's question>

## Rules:
- Start by understanding the question, then systematically explore
- Use search_files and search_code first to find relevant code
- Then read_file or read_function to examine details
- Use trace_dependencies to understand impact and connections
- Use get_analysis_section to get pre-computed insights
- Each tool call should build on what you learned from previous calls
- When you have enough information (typically 3-6 tool calls), synthesize an answer
- Your final ANSWER should be detailed, reference specific files/functions, and be actionable
- Do NOT repeat the same tool call with the same input
- PREFER get_analysis_section first — it has pre-computed insights that answer many questions instantly
- Keep answers concise and focused on the question"""


class AgentEngine:
    """ReAct-style agent that autonomously explores codebases."""

    def _compress_history(self, messages: list[str]) -> list[str]:
        """Compress older messages to stay within prompt budget."""
        full = "\n\n".join(messages)
        if len(full) <= MAX_PROMPT_CHARS:
            return messages

        # Keep first message (question) and last 2 steps intact
        # Summarize everything in between
        if len(messages) <= 3:
            return messages

        compressed = [messages[0]]  # Keep the question

        # Summarize middle messages (older steps)
        for msg in messages[1:-2]:
            # Extract just the key info: tool name + brief observation
            lines = msg.split("\n")
            summary_lines = []
            for line in lines:
                if line.startswith("THINK:") or line.startswith("ACTION:") or line.startswith("INPUT:"):
                    summary_lines.append(line)
                elif line.startswith("OBSERVATION:"):
                    obs = line[len("OBSERVATION:"):].strip()
                    # Keep only first 200 chars of observation
                    summary_lines.append(f"OBSERVATION: {obs[:200]}{'...' if len(obs) > 200 else ''}")
            if summary_lines:
                compressed.append("\n".join(summary_lines))

        # Keep last 2 messages intact (most recent context)
        compressed.extend(messages[-2:])
        return compressed

    async def run(
        self,
        question: str,
        tools: AgentTools,
    ) -> AsyncGenerator[dict, None]:
        """Run the agent loop, yielding step events.

        Each yielded event has:
          {"type": "think"|"action"|"observation"|"answer"|"error", "content": str, "step": int}
        """
        tool_descriptions = tools.get_tool_descriptions_prompt()
        system = AGENT_SYSTEM_PROMPT.format(tools=tool_descriptions)

        # Build conversation history for the agent
        messages = [
            f"User question: {question}\n\n"
            f"Begin by thinking about what you need to explore to answer this question."
        ]

        step = 0
        while step < MAX_STEPS:
            step += 1
            t0 = time.monotonic()

            # Compress history if prompt is getting too large
            messages = self._compress_history(messages)

            # Build full prompt from conversation history
            prompt = "\n\n".join(messages)

            # Get agent's next action (use "agent" task → fast model for speed)
            try:
                response = await model_router.generate(
                    "agent", prompt, system_prompt=system
                )
            except Exception as e:
                yield {"type": "error", "content": f"LLM error: {e}", "step": step}
                break

            response = response.strip()
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            # Parse the response
            parsed = self._parse_response(response)

            if parsed["type"] == "answer":
                # Emit think if present
                if parsed.get("think"):
                    yield {"type": "think", "content": parsed["think"], "step": step, "duration_ms": elapsed_ms}

                # Final answer
                yield {"type": "answer", "content": parsed["answer"], "step": step, "duration_ms": elapsed_ms}
                return

            elif parsed["type"] == "action":
                # Emit think
                if parsed.get("think"):
                    yield {"type": "think", "content": parsed["think"], "step": step, "duration_ms": elapsed_ms}

                # Emit action
                tool_name = parsed["action"]
                tool_input = parsed["input"]
                yield {
                    "type": "action",
                    "content": f"{tool_name}: {tool_input}",
                    "tool": tool_name,
                    "tool_input": tool_input,
                    "step": step,
                    "duration_ms": elapsed_ms,
                }

                # Execute tool
                t_tool = time.monotonic()
                observation = await tools.execute_tool(tool_name, tool_input)
                tool_ms = int((time.monotonic() - t_tool) * 1000)

                # Truncate very long observations
                if len(observation) > 1500:
                    observation = observation[:1500] + "\n... (truncated)"

                yield {
                    "type": "observation",
                    "content": observation,
                    "step": step,
                    "duration_ms": tool_ms,
                }

                # Add to conversation history
                messages.append(
                    f"Step {step}:\n"
                    f"THINK: {parsed.get('think', '')}\n"
                    f"ACTION: {tool_name}\n"
                    f"INPUT: {tool_input}\n"
                    f"OBSERVATION: {observation}\n"
                )

            else:
                # Couldn't parse — treat as thinking, ask to continue
                yield {"type": "think", "content": response[:500], "step": step, "duration_ms": elapsed_ms}
                messages.append(
                    f"Step {step} (your response was not in the correct format):\n"
                    f"{response[:500]}\n\n"
                    f"Please respond with either:\n"
                    f"THINK: ... ACTION: ... INPUT: ...\n"
                    f"OR\n"
                    f"THINK: ... ANSWER: ..."
                )

        # Exhausted max steps — force a final answer
        messages = self._compress_history(messages)
        messages.append(
            f"\nYou have used all {MAX_STEPS} steps. "
            f"Based on everything you've learned, provide your final ANSWER now."
        )
        prompt = "\n\n".join(messages)
        try:
            response = await model_router.generate("agent", prompt, system_prompt=system)
            parsed = self._parse_response(response)
            answer = parsed.get("answer") or parsed.get("think") or response
            yield {"type": "answer", "content": answer, "step": step + 1}
        except Exception as e:
            yield {"type": "error", "content": f"Failed to generate final answer: {e}", "step": step + 1}

    def _parse_response(self, text: str) -> dict:
        """Parse agent response into structured components."""
        result = {"type": "unknown"}

        # Extract THINK
        think_match = re.search(r'THINK:\s*(.+?)(?=\n(?:ACTION|ANSWER):|\Z)', text, re.DOTALL)
        if think_match:
            result["think"] = think_match.group(1).strip()

        # Check for ANSWER (final response)
        answer_match = re.search(r'ANSWER:\s*(.+)', text, re.DOTALL)
        if answer_match:
            result["type"] = "answer"
            result["answer"] = answer_match.group(1).strip()
            return result

        # Check for ACTION + INPUT
        action_match = re.search(r'ACTION:\s*(\S+)', text)
        input_match = re.search(r'INPUT:\s*(.+?)(?=\n(?:THINK|ACTION|ANSWER):|\Z)', text, re.DOTALL)

        if action_match:
            result["type"] = "action"
            result["action"] = action_match.group(1).strip()
            result["input"] = input_match.group(1).strip() if input_match else ""
            return result

        return result


agent_engine = AgentEngine()
