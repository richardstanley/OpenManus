from typing import Any

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.python_execute import PythonExecute
from app.tool.web_search import WebSearch


class Manus(ToolCallAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends ToolCallAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    
    The Manus agent is the primary interface for users to interact with the OpenManus
    system, providing a unified way to access multiple AI capabilities through a
    single agent.
    """

    # Basic agent identification
    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    # Prompts that guide the agent's behavior
    system_prompt: str = SYSTEM_PROMPT  # Defines the agent's overall capabilities and constraints
    next_step_prompt: str = NEXT_STEP_PROMPT  # Used to determine the next action in a sequence

    # Execution limits to prevent infinite loops or excessive resource usage
    max_observe: int = 2000  # Maximum observation length
    max_steps: int = 20  # Maximum number of steps before termination

    # Tool configuration - equips the agent with various capabilities
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),  # Allows executing Python code
            WebSearch(),      # Enables web search capabilities
            BrowserUseTool(), # Provides web browsing functionality
            FileSaver(),      # Allows saving files to disk
            Terminate()       # Provides a way to terminate execution
        )
    )

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """
        Handle special tools that require custom processing.
        
        This method extends the base implementation to ensure proper cleanup
        of browser resources when terminating execution.
        
        Args:
            name: The name of the tool being handled
            result: The result from the tool execution
            **kwargs: Additional arguments
        """
        if not self._is_special_tool(name):
            return
        else:
            # Ensure browser resources are cleaned up before termination
            await self.available_tools.get_tool(BrowserUseTool().name).cleanup()
            # Call the parent implementation for standard termination handling
            await super()._handle_special_tool(name, result, **kwargs)
