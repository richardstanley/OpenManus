from typing import List

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.swe import NEXT_STEP_TEMPLATE, SYSTEM_PROMPT
from app.tool import Bash, StrReplaceEditor, Terminate, ToolCollection


class SWEAgent(ToolCallAgent):
    """
    An agent that implements the SWEAgent paradigm for executing code and natural conversations.
    
    The SWEAgent (Software Engineering Agent) is specialized for programming tasks,
    equipped with tools for interacting with the terminal and editing code files.
    It extends the ToolCallAgent with software engineering specific capabilities,
    allowing it to navigate the file system, execute commands, and modify code.
    
    This agent is designed to function as an autonomous AI programmer that can
    directly interact with the computer to solve programming and development tasks.
    """

    # Basic agent identification
    name: str = "swe"
    description: str = "an autonomous AI programmer that interacts directly with the computer to solve tasks."

    # Prompts that guide the agent's behavior
    system_prompt: str = SYSTEM_PROMPT  # Defines the agent's software engineering capabilities
    next_step_prompt: str = NEXT_STEP_TEMPLATE  # Template for determining the next action, includes working directory

    # Tool configuration - equips the agent with software engineering capabilities
    available_tools: ToolCollection = ToolCollection(
        Bash(),              # Tool for executing terminal commands
        StrReplaceEditor(),  # Tool for editing code files
        Terminate()          # Tool for terminating execution
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])  # Tools with special handling

    # Execution limits
    max_steps: int = 30  # Maximum number of steps before termination

    # Software engineering specific attributes
    bash: Bash = Field(default_factory=Bash)  # Dedicated Bash tool instance for working directory management
    working_dir: str = "."  # Current working directory, initialized to the current directory

    async def think(self) -> bool:
        """
        Process current state and decide next action with awareness of the working directory.
        
        This method extends the base think method to update the working directory
        before each thinking cycle and include it in the prompt. This ensures the
        agent always has the correct context about its current location in the
        file system when making decisions.
        
        Returns:
            bool: True if thinking was successful and actions were determined,
                  False otherwise
        """
        # Update working directory by executing 'pwd' command
        self.working_dir = await self.bash.execute("pwd")
        
        # Format the next step prompt with the current directory
        self.next_step_prompt = self.next_step_prompt.format(
            current_dir=self.working_dir
        )

        # Call the parent class's think method with the updated prompt
        return await super().think()
