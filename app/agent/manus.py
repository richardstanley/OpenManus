"""
Core implementation of the Manus agent.
This module defines the main agent class that orchestrates all operations and tool usage.
"""

from typing import Optional

from pydantic import Field, model_validator

from app.agent.browser import BrowserContextHelper
from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor


class Manus(ToolCallAgent):
    """
    A versatile general-purpose agent that can solve various tasks using multiple tools.

    This agent is designed to:
    1. Process user requests through multiple steps
    2. Select and use appropriate tools for each step
    3. Maintain context and memory between steps
    4. Handle browser automation when needed
    5. Clean up resources properly

    Attributes:
        name (str): Name of the agent
        description (str): Description of the agent's capabilities
        system_prompt (str): System prompt that defines agent behavior
        next_step_prompt (str): Prompt used for determining next actions
        max_observe (int): Maximum number of characters to observe in context
        max_steps (int): Maximum number of steps allowed per task
        available_tools (ToolCollection): Collection of tools the agent can use
        special_tool_names (list[str]): Names of special tools (e.g., Terminate)
        browser_context_helper (Optional[BrowserContextHelper]): Helper for browser automation
    """

    # Basic agent information
    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    # System prompts for agent behavior
    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Operational limits
    max_observe: int = 10000  # Maximum characters to observe
    max_steps: int = 20      # Maximum steps per task

    # Initialize the collection of available tools
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),      # For running Python code
            BrowserUseTool(),     # For web automation
            StrReplaceEditor(),   # For text manipulation
            Terminate()           # For ending the task
        )
    )

    # Special tools that have unique handling
    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    # Browser context management
    browser_context_helper: Optional[BrowserContextHelper] = None

    @model_validator(mode="after")
    def initialize_helper(self) -> "Manus":
        """
        Initialize the browser context helper after model validation.
        This ensures proper setup of browser automation capabilities.

        Returns:
            Manus: The initialized agent instance
        """
        self.browser_context_helper = BrowserContextHelper(self)
        return self

    async def think(self) -> bool:
        """
        Process current state and decide next actions with appropriate context.

        This method:
        1. Manages browser context when needed
        2. Updates prompts based on current state
        3. Delegates to parent class for core thinking logic
        4. Restores original prompt after processing

        Returns:
            bool: True if thinking process completed successfully
        """
        # Store original prompt for restoration
        original_prompt = self.next_step_prompt

        # Get recent message history for context
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []

        # Check if browser tool was recently used
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )

        # Update prompt if browser context is needed
        if browser_in_use:
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        # Perform core thinking process
        result = await super().think()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result

    async def cleanup(self):
        """
        Clean up Manus agent resources.
        Ensures proper cleanup of browser context and other resources.
        """
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
