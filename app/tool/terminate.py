from app.tool.base import BaseTool


_TERMINATE_DESCRIPTION = """Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.
When you have finished all the tasks, call this tool to end the work."""


class Terminate(BaseTool):
    """
    A tool for gracefully ending agent interactions with a specified status.
    
    This tool provides a standardized way for agents to signal that they have
    completed their assigned tasks or cannot proceed further. It serves as an
    explicit termination mechanism, allowing agents to communicate the outcome
    of their work (success or failure) and cleanly exit the interaction flow.
    
    The Terminate tool is typically used in these scenarios:
    1. When all requested tasks have been successfully completed
    2. When the agent has reached an insurmountable obstacle and cannot continue
    3. As part of a controlled shutdown sequence in multi-step workflows
    
    By requiring a status parameter, the tool ensures that termination is always
    accompanied by clear information about the outcome, which can be used for
    logging, reporting, or triggering subsequent processes.
    """

    # Tool identification and interface definition
    name: str = "terminate"
    description: str = _TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "The finish status of the interaction.",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    async def execute(self, status: str) -> str:
        """
        Finish the current execution with the specified status.
        
        This method handles the termination process, providing a confirmation
        message that includes the final status. The actual termination mechanism
        is typically implemented at a higher level in the agent's execution loop,
        which monitors for calls to this tool and handles the shutdown process.
        
        The method enforces a binary outcome model (success/failure) to ensure
        clear and unambiguous termination states that can be easily processed
        by other components in the system.
        
        Args:
            status (str): The final status of the interaction, either "success" or "failure".
                         "success" indicates all tasks were completed satisfactorily.
                         "failure" indicates the agent could not complete the assigned tasks.
        
        Returns:
            str: A confirmation message indicating that the interaction has been terminated
                 and including the final status for reference.
        """
        return f"The interaction has been completed with status: {status}"
