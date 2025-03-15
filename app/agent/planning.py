import time
from typing import Dict, List, Optional

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.prompt.planning import NEXT_STEP_PROMPT, PLANNING_SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, Message, ToolCall, ToolChoice
from app.tool import PlanningTool, Terminate, ToolCollection


class PlanningAgent(ToolCallAgent):
    """
    An agent that creates and manages plans to solve tasks.

    This agent uses a planning tool to create and manage structured plans,
    and tracks progress through individual steps until task completion.
    
    The PlanningAgent extends the ToolCallAgent with planning-specific capabilities,
    allowing it to break down complex tasks into manageable steps, track progress,
    and execute each step in sequence until the entire plan is completed.
    """

    # Basic agent identification
    name: str = "planning"
    description: str = "An agent that creates and manages plans to solve tasks"

    # Prompts that guide the agent's behavior
    system_prompt: str = PLANNING_SYSTEM_PROMPT  # Defines the agent's planning capabilities
    next_step_prompt: str = NEXT_STEP_PROMPT  # Used to determine the next step in the plan

    # Tool configuration - equips the agent with planning capabilities
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PlanningTool(),  # Tool for creating and managing plans
            Terminate()      # Tool for terminating execution
        )
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore  # Controls how tools are selected
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])  # Tools with special handling

    # Storage for active tool calls
    tool_calls: List[ToolCall] = Field(default_factory=list)
    
    # Plan tracking
    active_plan_id: Optional[str] = Field(default=None)  # ID of the currently active plan

    # Execution tracking - maps tool call IDs to step information
    step_execution_tracker: Dict[str, Dict] = Field(default_factory=dict)  # Tracks which tool calls are associated with which steps
    current_step_index: Optional[int] = None  # Index of the current step being executed

    # Execution limits
    max_steps: int = 20  # Maximum number of steps before termination

    @model_validator(mode="after")
    def initialize_plan_and_verify_tools(self) -> "PlanningAgent":
        """
        Initialize the agent with a default plan ID and validate required tools.
        
        This validator runs after the model is created to ensure the agent has
        a unique plan ID and the necessary planning tool is available.
        
        Returns:
            PlanningAgent: The initialized agent instance
        """
        # Generate a unique plan ID based on the current timestamp
        self.active_plan_id = f"plan_{int(time.time())}"

        # Ensure the planning tool is available
        if "planning" not in self.available_tools.tool_map:
            self.available_tools.add_tool(PlanningTool())

        return self

    async def think(self) -> bool:
        """
        Decide the next action based on plan status.
        
        This method extends the base think method to include the current plan status
        in the prompt, helping the agent make decisions in the context of the overall plan.
        
        Returns:
            bool: True if thinking was successful and actions were determined,
                  False otherwise
        """
        # Create a prompt that includes the current plan status if a plan exists
        prompt = (
            f"CURRENT PLAN STATUS:\n{await self.get_plan()}\n\n{self.next_step_prompt}"
            if self.active_plan_id
            else self.next_step_prompt
        )
        self.messages.append(Message.user_message(prompt))

        # Get the current step index before thinking
        self.current_step_index = await self._get_current_step_index()

        # Call the parent class's think method
        result = await super().think()

        # After thinking, if we decided to execute a tool and it's not a planning tool or special tool,
        # associate it with the current step for tracking
        if result and self.tool_calls:
            latest_tool_call = self.tool_calls[0]  # Get the most recent tool call
            if (
                latest_tool_call.function.name != "planning"
                and latest_tool_call.function.name not in self.special_tool_names
                and self.current_step_index is not None
            ):
                # Track this tool call as part of the current step execution
                self.step_execution_tracker[latest_tool_call.id] = {
                    "step_index": self.current_step_index,
                    "tool_name": latest_tool_call.function.name,
                    "status": "pending",  # Will be updated after execution
                }

        return result

    async def act(self) -> str:
        """
        Execute a step and track its completion status.
        
        This method extends the base act method to update the plan status
        after a tool has been executed, marking steps as completed when appropriate.
        
        Returns:
            str: The result of the action execution
        """
        # Call the parent class's act method to execute the tool
        result = await super().act()

        # After executing the tool, update the plan status
        if self.tool_calls:
            latest_tool_call = self.tool_calls[0]

            # Update the execution status to completed
            if latest_tool_call.id in self.step_execution_tracker:
                self.step_execution_tracker[latest_tool_call.id]["status"] = "completed"
                self.step_execution_tracker[latest_tool_call.id]["result"] = result

                # Update the plan status if this was a non-planning, non-special tool
                if (
                    latest_tool_call.function.name != "planning"
                    and latest_tool_call.function.name not in self.special_tool_names
                ):
                    # Mark the corresponding step as completed in the plan
                    await self.update_plan_status(latest_tool_call.id)

        return result

    async def get_plan(self) -> str:
        """
        Retrieve the current plan status.
        
        This method queries the planning tool to get the current state of the plan,
        including which steps are completed, in progress, or not yet started.
        
        Returns:
            str: A formatted string representation of the current plan
        """
        if not self.active_plan_id:
            return "No active plan. Please create a plan first."

        # Execute the planning tool to get the current plan
        result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id},
        )
        return result.output if hasattr(result, "output") else str(result)

    async def run(self, request: Optional[str] = None) -> str:
        """
        Run the agent with an optional initial request.
        
        This method extends the base run method to create an initial plan
        if a request is provided before starting the execution cycle.
        
        Args:
            request: Optional initial user request to process
            
        Returns:
            str: A string summarizing the execution results
        """
        if request:
            # Create an initial plan based on the request
            await self.create_initial_plan(request)
        return await super().run()

    async def update_plan_status(self, tool_call_id: str) -> None:
        """
        Update the current plan progress based on completed tool execution.
        
        This method marks a step as completed in the plan if the associated tool
        has been successfully executed. It ensures that plan progress accurately
        reflects the actual execution status.
        
        Args:
            tool_call_id: The ID of the tool call that was executed
        """
        if not self.active_plan_id:
            return

        # Check if we're tracking this tool call
        if tool_call_id not in self.step_execution_tracker:
            logger.warning(f"No step tracking found for tool call {tool_call_id}")
            return

        # Get the tracker for this tool call
        tracker = self.step_execution_tracker[tool_call_id]
        if tracker["status"] != "completed":
            logger.warning(f"Tool call {tool_call_id} has not completed successfully")
            return

        step_index = tracker["step_index"]

        try:
            # Mark the step as completed in the plan
            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "mark_step",
                    "plan_id": self.active_plan_id,
                    "step_index": step_index,
                    "step_status": "completed",
                },
            )
            logger.info(
                f"Marked step {step_index} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")

    async def _get_current_step_index(self) -> Optional[int]:
        """
        Parse the current plan to identify the first non-completed step's index.
        
        This method analyzes the plan text to find the next step that needs to be
        executed (either not started or in progress), and marks it as in progress.
        
        Returns:
            Optional[int]: The index of the current step, or None if no active step is found
        """
        if not self.active_plan_id:
            return None

        # Get the current plan
        plan = await self.get_plan()

        try:
            plan_lines = plan.splitlines()
            steps_index = -1

            # Find the index of the "Steps:" line
            for i, line in enumerate(plan_lines):
                if line.strip() == "Steps:":
                    steps_index = i
                    break

            if steps_index == -1:
                return None

            # Find the first non-completed step
            for i, line in enumerate(plan_lines[steps_index + 1 :], start=0):
                if "[ ]" in line or "[→]" in line:  # not_started or in_progress
                    # Mark current step as in_progress
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "mark_step",
                            "plan_id": self.active_plan_id,
                            "step_index": i,
                            "step_status": "in_progress",
                        },
                    )
                    return i

            return None  # No active step found
        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None

    async def create_initial_plan(self, request: str) -> None:
        """
        Create an initial plan based on the request.
        
        This method uses the LLM to analyze the user's request and create
        a structured plan with steps to accomplish the task. It adds the
        plan creation to the agent's memory for context in future steps.
        
        Args:
            request: The user's request to be analyzed and planned
        """
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        # Create a message asking the LLM to analyze the request and create a plan
        messages = [
            Message.user_message(
                f"Analyze the request and create a plan with ID {self.active_plan_id}: {request}"
            )
        ]
        self.memory.add_messages(messages)
        
        # Get response with tool options from the LLM
        response = await self.llm.ask_tool(
            messages=messages,
            system_msgs=[Message.system_message(self.system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice=ToolChoice.AUTO,
        )
        assistant_msg = Message.from_tool_calls(
            content=response.content, tool_calls=response.tool_calls
        )

        self.memory.add_message(assistant_msg)

        # Execute the planning tool to create the plan
        plan_created = False
        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                result = await self.execute_tool(tool_call)
                logger.info(
                    f"Executed tool {tool_call.function.name} with result: {result}"
                )

                # Add tool response to memory
                tool_msg = Message.tool_message(
                    content=result,
                    tool_call_id=tool_call.id,
                    name=tool_call.function.name,
                )
                self.memory.add_message(tool_msg)
                plan_created = True
                break

        # Handle case where no plan was created
        if not plan_created:
            logger.warning("No plan created from initial request")
            tool_msg = Message.assistant_message(
                "Error: Parameter `plan_id` is required for command: create"
            )
            self.memory.add_message(tool_msg)


# Example usage of the PlanningAgent
async def main():
    """
    Example function demonstrating how to use the PlanningAgent.
    
    This function creates a PlanningAgent instance, configures it with
    the necessary tools, and runs it with a sample request.
    """
    # Configure and run the agent
    agent = PlanningAgent(available_tools=ToolCollection(PlanningTool(), Terminate()))
    result = await agent.run("Help me plan a trip to the moon")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
