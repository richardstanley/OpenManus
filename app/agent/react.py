from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.schema import AgentState, Memory


class ReActAgent(BaseAgent, ABC):
    """
    Abstract base class implementing the ReAct (Reasoning and Acting) pattern for agents.
    
    The ReAct pattern is a problem-solving approach where the agent alternates between
    reasoning about the current state (thinking) and taking actions based on that reasoning.
    This pattern enables more deliberate and explainable decision-making by the agent.
    
    This class extends BaseAgent with the core ReAct pattern implementation and
    requires subclasses to implement the specific thinking and acting logic.
    """

    # Basic agent identification
    name: str  # Required name for the agent, to be defined by subclasses
    description: Optional[str] = None  # Optional description of the agent's capabilities

    # Prompts that guide the agent's behavior
    system_prompt: Optional[str] = None  # System-level instructions for the agent
    next_step_prompt: Optional[str] = None  # Prompt for determining the next action

    # Core dependencies and state management
    llm: Optional[LLM] = Field(default_factory=LLM)  # Language model for reasoning
    memory: Memory = Field(default_factory=Memory)  # Memory store for context
    state: AgentState = AgentState.IDLE  # Current state of the agent

    # Execution control parameters
    max_steps: int = 10  # Maximum number of steps before termination
    current_step: int = 0  # Current step in execution

    @abstractmethod
    async def think(self) -> bool:
        """
        Process current state and decide next action.
        
        This abstract method must be implemented by subclasses to define
        the reasoning logic of the agent. It analyzes the current context
        and determines what action(s) to take next.
        
        Returns:
            bool: True if an action should be taken, False otherwise
        """
        pass

    @abstractmethod
    async def act(self) -> str:
        """
        Execute decided actions.
        
        This abstract method must be implemented by subclasses to define
        the action execution logic of the agent. It carries out the actions
        determined during the thinking phase.
        
        Returns:
            str: The result of the action execution
        """
        pass

    async def step(self) -> str:
        """
        Execute a single step in the ReAct cycle: think and act.
        
        This method implements one complete cycle of the ReAct pattern by:
        1. Calling the think method to reason about the current state
        2. If thinking indicates an action is needed, calling the act method
        
        This creates the alternating pattern of reasoning and acting that
        characterizes the ReAct approach.
        
        Returns:
            str: The result of the step execution
        """
        # First, think about what to do
        should_act = await self.think()
        
        # If thinking indicates no action is needed, return early
        if not should_act:
            return "Thinking complete - no action needed"
        
        # Otherwise, execute the decided action
        return await self.act()
