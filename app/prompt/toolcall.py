"""
Prompt templates for the general-purpose tool-calling agent in the OpenManus framework.

This module defines minimal prompt templates that establish a basic tool-calling
agent without the specialized constraints of domain-specific agents. These prompts
provide a foundation for agents that need to use tools but don't require the
structured environment of more specialized agents like the SWE (Software Engineering) agent.
"""

# The system prompt that establishes the agent's basic identity and capability
# This is intentionally minimal to allow the agent maximum flexibility in tool usage
SYSTEM_PROMPT = "You are an agent that can execute tool calls"

# Additional instruction provided after each agent response
# This reminds the agent about the termination mechanism to properly end interactions
NEXT_STEP_PROMPT = (
    "If you want to stop interaction, use `terminate` tool/function call."
)
