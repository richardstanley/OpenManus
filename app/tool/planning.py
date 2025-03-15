# tool/planning.py
from typing import Dict, List, Literal, Optional

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult


# Description of the planning tool for the LLM
_PLANNING_TOOL_DESCRIPTION = """
A planning tool that allows the agent to create and manage plans for solving complex tasks.
The tool provides functionality for creating plans, updating plan steps, and tracking progress.
"""


class PlanningTool(BaseTool):
    """
    A planning tool that allows the agent to create and manage plans for solving complex tasks.
    
    This tool enables agents to break down complex problems into manageable steps,
    track progress on those steps, and maintain multiple plans simultaneously.
    It provides a structured approach to task management with features for
    creating, updating, and monitoring plans.
    
    The tool maintains state between invocations, allowing for persistent
    plan management throughout an agent's execution lifecycle.
    """

    # Tool identification and interface definition
    name: str = "planning"
    description: str = _PLANNING_TOOL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: create, update, list, get, set_active, mark_step, delete.",
                "enum": [
                    "create",
                    "update",
                    "list",
                    "get",
                    "set_active",
                    "mark_step",
                    "delete",
                ],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan. Required for create, update, set_active, and delete commands. Optional for get and mark_step (uses active plan if not specified).",
                "type": "string",
            },
            "title": {
                "description": "Title for the plan. Required for create command, optional for update command.",
                "type": "string",
            },
            "steps": {
                "description": "List of plan steps. Required for create command, optional for update command.",
                "type": "array",
                "items": {"type": "string"},
            },
            "step_index": {
                "description": "Index of the step to update (0-based). Required for mark_step command.",
                "type": "integer",
            },
            "step_status": {
                "description": "Status to set for a step. Used with mark_step command.",
                "enum": ["not_started", "in_progress", "completed", "blocked"],
                "type": "string",
            },
            "step_notes": {
                "description": "Additional notes for a step. Optional for mark_step command.",
                "type": "string",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    # State storage for plans and tracking the active plan
    plans: dict = {}  # Dictionary to store plans by plan_id
    _current_plan_id: Optional[str] = None  # Track the current active plan

    async def execute(
        self,
        *,
        command: Literal[
            "create", "update", "list", "get", "set_active", "mark_step", "delete"
        ],
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_index: Optional[int] = None,
        step_status: Optional[
            Literal["not_started", "in_progress", "completed", "blocked"]
        ] = None,
        step_notes: Optional[str] = None,
        **kwargs,
    ):
        """
        Execute the planning tool with the given command and parameters.
        
        This method is the main entry point for all planning operations. It validates
        the command and dispatches to the appropriate method based on the command.
        
        Parameters:
            command: The operation to perform (create, update, list, get, set_active, mark_step, delete)
            plan_id: Unique identifier for the plan
            title: Title for the plan (used with create and update commands)
            steps: List of steps for the plan (used with create and update commands)
            step_index: Index of the step to update (used with mark_step command)
            step_status: Status to set for a step (used with mark_step command)
            step_notes: Additional notes for a step (used with mark_step command)
            
        Returns:
            ToolResult containing the result of the operation
            
        Raises:
            ToolError: If the command is invalid or required parameters are missing
        """
        # Dispatch to the appropriate method based on the command
        if command == "create":
            return self._create_plan(plan_id, title, steps)
        elif command == "update":
            return self._update_plan(plan_id, title, steps)
        elif command == "list":
            return self._list_plans()
        elif command == "get":
            return self._get_plan(plan_id)
        elif command == "set_active":
            return self._set_active_plan(plan_id)
        elif command == "mark_step":
            return self._mark_step(plan_id, step_index, step_status, step_notes)
        elif command == "delete":
            return self._delete_plan(plan_id)
        else:
            # This should never happen due to the Literal type, but just in case
            raise ToolError(
                f"Unrecognized command: {command}. Allowed commands are: create, update, list, get, set_active, mark_step, delete"
            )

    def _create_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """
        Create a new plan with the given ID, title, and steps.
        
        This method creates a new plan with the specified parameters and
        initializes all steps with a 'not_started' status. The newly created
        plan becomes the active plan.
        
        Parameters:
            plan_id: Unique identifier for the plan
            title: Title for the plan
            steps: List of steps for the plan
            
        Returns:
            ToolResult containing the formatted plan details
            
        Raises:
            ToolError: If required parameters are missing or invalid
        """
        # Validate required parameters
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: create")

        if plan_id in self.plans:
            raise ToolError(
                f"A plan with ID '{plan_id}' already exists. Use 'update' to modify existing plans."
            )

        if not title:
            raise ToolError("Parameter `title` is required for command: create")

        if (
            not steps
            or not isinstance(steps, list)
            or not all(isinstance(step, str) for step in steps)
        ):
            raise ToolError(
                "Parameter `steps` must be a non-empty list of strings for command: create"
            )

        # Create a new plan with initialized step statuses
        plan = {
            "plan_id": plan_id,
            "title": title,
            "steps": steps,
            "step_statuses": ["not_started"] * len(steps),  # Initialize all steps as not started
            "step_notes": [""] * len(steps),  # Initialize empty notes for all steps
        }

        # Store the plan and set it as active
        self.plans[plan_id] = plan
        self._current_plan_id = plan_id  # Set as active plan

        # Return the formatted plan
        return ToolResult(
            output=f"Plan created successfully with ID: {plan_id}\n\n{self._format_plan(plan)}"
        )

    def _update_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """
        Update an existing plan with new title or steps.
        
        This method updates an existing plan with the specified parameters.
        When updating steps, it preserves the status and notes of unchanged steps
        and initializes new steps with a 'not_started' status.
        
        Parameters:
            plan_id: Unique identifier for the plan to update
            title: New title for the plan (optional)
            steps: New list of steps for the plan (optional)
            
        Returns:
            ToolResult containing the formatted updated plan
            
        Raises:
            ToolError: If plan_id is missing or invalid, or if steps are invalid
        """
        # Validate required parameters
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: update")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        # Get the existing plan
        plan = self.plans[plan_id]

        # Update the title if provided
        if title:
            plan["title"] = title

        # Update the steps if provided
        if steps:
            # Validate steps format
            if not isinstance(steps, list) or not all(
                isinstance(step, str) for step in steps
            ):
                raise ToolError(
                    "Parameter `steps` must be a list of strings for command: update"
                )

            # Preserve existing step statuses for unchanged steps
            old_steps = plan["steps"]
            old_statuses = plan["step_statuses"]
            old_notes = plan["step_notes"]

            # Create new step statuses and notes
            new_statuses = []
            new_notes = []

            # For each new step, preserve status and notes if the step exists at the same position
            for i, step in enumerate(steps):
                # If the step exists at the same position in old steps, preserve status and notes
                if i < len(old_steps) and step == old_steps[i]:
                    new_statuses.append(old_statuses[i])
                    new_notes.append(old_notes[i])
                else:
                    # Otherwise, initialize as not started with empty notes
                    new_statuses.append("not_started")
                    new_notes.append("")

            # Update the plan with new steps, statuses, and notes
            plan["steps"] = steps
            plan["step_statuses"] = new_statuses
            plan["step_notes"] = new_notes

        # Return the formatted updated plan
        return ToolResult(
            output=f"Plan updated successfully: {plan_id}\n\n{self._format_plan(plan)}"
        )

    def _list_plans(self) -> ToolResult:
        """
        List all available plans.
        
        This method returns a summary of all plans, including their IDs,
        titles, and progress information. It also indicates which plan
        is currently active.
        
        Returns:
            ToolResult containing the list of plans
        """
        # Check if there are any plans
        if not self.plans:
            return ToolResult(
                output="No plans available. Create a plan with the 'create' command."
            )

        # Build the output string with plan summaries
        output = "Available plans:\n"
        for plan_id, plan in self.plans.items():
            # Mark the active plan
            current_marker = " (active)" if plan_id == self._current_plan_id else ""
            
            # Calculate progress statistics
            completed = sum(
                1 for status in plan["step_statuses"] if status == "completed"
            )
            total = len(plan["steps"])
            progress = f"{completed}/{total} steps completed"
            
            # Add the plan summary to the output
            output += f"• {plan_id}{current_marker}: {plan['title']} - {progress}\n"

        return ToolResult(output=output)

    def _get_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Get details of a specific plan.
        
        This method returns the detailed information for a specific plan,
        including all steps, their statuses, and notes. If no plan_id is
        provided, it uses the current active plan.
        
        Parameters:
            plan_id: Unique identifier for the plan to retrieve (optional)
            
        Returns:
            ToolResult containing the formatted plan details
            
        Raises:
            ToolError: If no plan is found or no active plan exists
        """
        # If no plan_id is provided, use the current active plan
        if not plan_id:
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self._current_plan_id

        # Check if the plan exists
        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        # Get and format the plan
        plan = self.plans[plan_id]
        return ToolResult(output=self._format_plan(plan))

    def _set_active_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Set a plan as the active plan.
        
        This method sets the specified plan as the active plan, which
        becomes the default plan for operations that don't specify a plan_id.
        
        Parameters:
            plan_id: Unique identifier for the plan to set as active
            
        Returns:
            ToolResult containing the formatted plan details
            
        Raises:
            ToolError: If plan_id is missing or invalid
        """
        # Validate required parameters
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: set_active")

        # Check if the plan exists
        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        # Set the plan as active
        self._current_plan_id = plan_id
        return ToolResult(
            output=f"Plan '{plan_id}' is now the active plan.\n\n{self._format_plan(self.plans[plan_id])}"
        )

    def _mark_step(
        self,
        plan_id: Optional[str],
        step_index: Optional[int],
        step_status: Optional[str],
        step_notes: Optional[str],
    ) -> ToolResult:
        """
        Mark a step with a specific status and optional notes.
        
        This method updates the status and notes for a specific step in a plan.
        If no plan_id is provided, it uses the current active plan.
        
        Parameters:
            plan_id: Unique identifier for the plan (optional)
            step_index: Index of the step to update (0-based)
            step_status: New status for the step (not_started, in_progress, completed, blocked)
            step_notes: Additional notes for the step (optional)
            
        Returns:
            ToolResult containing the formatted updated plan
            
        Raises:
            ToolError: If required parameters are missing or invalid
        """
        # If no plan_id is provided, use the current active plan
        if not plan_id:
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self._current_plan_id

        # Check if the plan exists
        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        # Validate step_index
        if step_index is None:
            raise ToolError("Parameter `step_index` is required for command: mark_step")

        # Get the plan
        plan = self.plans[plan_id]

        # Validate step_index range
        if step_index < 0 or step_index >= len(plan["steps"]):
            raise ToolError(
                f"Invalid step_index: {step_index}. Valid indices range from 0 to {len(plan['steps'])-1}."
            )

        # Validate step_status
        if step_status and step_status not in [
            "not_started",
            "in_progress",
            "completed",
            "blocked",
        ]:
            raise ToolError(
                f"Invalid step_status: {step_status}. Valid statuses are: not_started, in_progress, completed, blocked"
            )

        # Update the step status if provided
        if step_status:
            plan["step_statuses"][step_index] = step_status

        # Update the step notes if provided
        if step_notes:
            plan["step_notes"][step_index] = step_notes

        # Return the formatted updated plan
        return ToolResult(
            output=f"Step {step_index} updated in plan '{plan_id}'.\n\n{self._format_plan(plan)}"
        )

    def _delete_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Delete a plan.
        
        This method removes a plan from the system. If the deleted plan
        was the active plan, it clears the active plan reference.
        
        Parameters:
            plan_id: Unique identifier for the plan to delete
            
        Returns:
            ToolResult containing a success message
            
        Raises:
            ToolError: If plan_id is missing or invalid
        """
        # Validate required parameters
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: delete")

        # Check if the plan exists
        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        # Delete the plan
        del self.plans[plan_id]

        # If the deleted plan was the active plan, clear the active plan
        if self._current_plan_id == plan_id:
            self._current_plan_id = None

        return ToolResult(output=f"Plan '{plan_id}' has been deleted.")

    def _format_plan(self, plan: Dict) -> str:
        """
        Format a plan for display.
        
        This utility method formats a plan into a human-readable string,
        including the title, progress statistics, and all steps with their
        statuses and notes.
        
        Parameters:
            plan: The plan dictionary to format
            
        Returns:
            A formatted string representation of the plan
        """
        # Format the plan header
        output = f"Plan: {plan['title']} (ID: {plan['plan_id']})\n"
        output += "=" * len(output) + "\n\n"

        # Calculate progress statistics
        total_steps = len(plan["steps"])
        completed = sum(1 for status in plan["step_statuses"] if status == "completed")
        in_progress = sum(
            1 for status in plan["step_statuses"] if status == "in_progress"
        )
        blocked = sum(1 for status in plan["step_statuses"] if status == "blocked")
        not_started = sum(
            1 for status in plan["step_statuses"] if status == "not_started"
        )

        # Format progress information
        output += f"Progress: {completed}/{total_steps} steps completed "
        if total_steps > 0:
            percentage = (completed / total_steps) * 100
            output += f"({percentage:.1f}%)\n"
        else:
            output += "(0%)\n"

        # Format status summary
        output += f"Status: {completed} completed, {in_progress} in progress, {blocked} blocked, {not_started} not started\n\n"
        output += "Steps:\n"

        # Format each step with its status and notes
        for i, (step, status, notes) in enumerate(
            zip(plan["steps"], plan["step_statuses"], plan["step_notes"])
        ):
            # Use symbols to represent different statuses
            status_symbol = {
                "not_started": "[ ]",  # Empty checkbox
                "in_progress": "[→]",  # Arrow for in progress
                "completed": "[✓]",    # Checkmark for completed
                "blocked": "[!]",      # Exclamation for blocked
            }.get(status, "[ ]")

            # Format the step with its index, status symbol, and description
            output += f"{i}. {status_symbol} {step}\n"
            
            # Add notes if they exist
            if notes:
                output += f"   Notes: {notes}\n"

        return output
